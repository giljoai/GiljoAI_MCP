# GiljoAI MCP - IIS Configuration for WAN (Windows Server)

## Prerequisites

- Windows Server 2019 or later
- IIS 10.0 or later
- Application Request Routing (ARR) 3.0+
- URL Rewrite 2.1+
- Valid SSL certificate (purchased or Let's Encrypt via win-acme)

## Installation Steps

### Step 1: Install IIS and Required Modules

**PowerShell (Run as Administrator)**:

```powershell
# Install IIS with required features
Install-WindowsFeature -name Web-Server -IncludeManagementTools
Install-WindowsFeature -name Web-Asp-Net45
Install-WindowsFeature -name Web-Net-Ext45
Install-WindowsFeature -name Web-AppInit
Install-WindowsFeature -name Web-WebSockets

# Restart IIS
iisreset
```

### Step 2: Install Application Request Routing (ARR)

1. Download Web Platform Installer: https://www.microsoft.com/web/downloads/platform.aspx
2. Launch Web Platform Installer
3. Search for "Application Request Routing 3.0"
4. Click "Add" then "Install"
5. Alternatively, direct download: https://www.iis.net/downloads/microsoft/application-request-routing

### Step 3: Install URL Rewrite Module

1. In Web Platform Installer, search for "URL Rewrite 2.1"
2. Click "Add" then "Install"
3. Alternatively, direct download: https://www.iis.net/downloads/microsoft/url-rewrite

### Step 4: Configure ARR Proxy

**IIS Manager**:

1. Open IIS Manager
2. Select server node (root level)
3. Double-click "Application Request Routing Cache"
4. Click "Server Proxy Settings" in Actions pane
5. Check "Enable proxy"
6. Set "Response buffer threshold (KB)" to 0 (for WebSocket support)
7. Set "Timeout (seconds)" to 3600
8. Click "Apply"

### Step 5: Create Website

**PowerShell**:

```powershell
# Create application pool
New-WebAppPool -Name "GiljoAI-MCP-Pool"
Set-ItemProperty IIS:\AppPools\GiljoAI-MCP-Pool -Name managedRuntimeVersion -Value ""
Set-ItemProperty IIS:\AppPools\GiljoAI-MCP-Pool -Name enable32BitAppOnWin64 -Value $false

# Create website directory
New-Item -ItemType Directory -Path "C:\inetpub\giljo-mcp" -Force

# Create website
New-Website -Name "GiljoAI-MCP" `
    -PhysicalPath "C:\inetpub\giljo-mcp" `
    -ApplicationPool "GiljoAI-MCP-Pool" `
    -Port 80 `
    -HostHeader "yourdomain.com"

# Add HTTPS binding (after SSL certificate is installed)
# New-WebBinding -Name "GiljoAI-MCP" -Protocol https -Port 443 -HostHeader "yourdomain.com"
```

### Step 6: Install SSL Certificate

#### Option A: Commercial Certificate

1. Generate CSR in IIS Manager:
   - Select server node → Server Certificates → Create Certificate Request
   - Fill in details (Common Name = yourdomain.com)
   - Save CSR to file
   - Submit to Certificate Authority
2. Complete Certificate Request:
   - Server Certificates → Complete Certificate Request
   - Select certificate file from CA
   - Friendly name: "GiljoAI MCP Production"
3. Bind certificate to site:
   - Select website → Bindings → Add
   - Type: https, Port: 443
   - Select SSL certificate

#### Option B: Let's Encrypt (Free)

Install win-acme (ACME client for Windows):

```powershell
# Download win-acme
Invoke-WebRequest -Uri "https://github.com/win-acme/win-acme/releases/download/v2.2.7/win-acme.v2.2.7.1613.x64.pluggable.zip" -OutFile "C:\win-acme.zip"
Expand-Archive -Path "C:\win-acme.zip" -DestinationPath "C:\win-acme"

# Run win-acme
cd C:\win-acme
.\wacs.exe

# Follow prompts:
# - Select "N" for new certificate
# - Select "1" for single binding
# - Select your IIS site
# - Provide email for Let's Encrypt
# - Accept Terms of Service
# - Choose automatic renewal (recommended)
```

### Step 7: Configure URL Rewrite Rules

Create `web.config` in `C:\inetpub\giljo-mcp`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <!-- URL Rewrite Module -->
        <rewrite>
            <rules>
                <!-- Force HTTPS -->
                <rule name="Force HTTPS" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions logicalGrouping="MatchAll" trackAllCaptures="false">
                        <add input="{HTTPS}" pattern="off" />
                    </conditions>
                    <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
                </rule>

                <!-- WebSocket Proxy -->
                <rule name="WebSocket Proxy" stopProcessing="true">
                    <match url="^ws$" />
                    <action type="Rewrite" url="http://localhost:7272/ws" />
                    <serverVariables>
                        <set name="HTTP_SEC_WEBSOCKET_EXTENSIONS" value="" />
                    </serverVariables>
                </rule>

                <!-- API Proxy with Rate Limiting -->
                <rule name="API Proxy" stopProcessing="true">
                    <match url="^api/(.*)" />
                    <action type="Rewrite" url="http://localhost:7272/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_PROTO" value="https" />
                        <set name="HTTP_X_REAL_IP" value="{REMOTE_ADDR}" />
                    </serverVariables>
                </rule>

                <!-- Health Checks -->
                <rule name="Health Check" stopProcessing="true">
                    <match url="^(health|ready)$" />
                    <action type="Rewrite" url="http://localhost:7272/{R:1}" />
                </rule>

                <!-- SPA Fallback (Vue Router) -->
                <rule name="SPA Fallback" stopProcessing="true">
                    <match url=".*" />
                    <conditions logicalGrouping="MatchAll">
                        <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
                        <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
                        <add input="{REQUEST_URI}" pattern="^/api/" negate="true" />
                        <add input="{REQUEST_URI}" pattern="^/ws$" negate="true" />
                    </conditions>
                    <action type="Rewrite" url="/" />
                </rule>
            </rules>

            <!-- Outbound rules for security headers -->
            <outboundRules>
                <rule name="Add HSTS Header" preCondition="HTTPS">
                    <match serverVariable="RESPONSE_Strict-Transport-Security" pattern=".*" />
                    <action type="Rewrite" value="max-age=63072000; includeSubDomains; preload" />
                </rule>
                <preConditions>
                    <preCondition name="HTTPS">
                        <add input="{HTTPS}" pattern="on" />
                    </preCondition>
                </preConditions>
            </outboundRules>
        </rewrite>

        <!-- Security Headers -->
        <httpProtocol>
            <customHeaders>
                <add name="X-Frame-Options" value="DENY" />
                <add name="X-Content-Type-Options" value="nosniff" />
                <add name="X-XSS-Protection" value="1; mode=block" />
                <add name="Referrer-Policy" value="no-referrer-when-downgrade" />
                <add name="Content-Security-Policy" value="default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss://yourdomain.com https://yourdomain.com; frame-ancestors 'none';" />
                <add name="Permissions-Policy" value="geolocation=(), microphone=(), camera=(), payment=()" />
                <remove name="X-Powered-By" />
                <remove name="Server" />
            </customHeaders>
        </httpProtocol>

        <!-- Request Filtering -->
        <security>
            <requestFiltering>
                <!-- Limit request size to 100MB -->
                <requestLimits maxAllowedContentLength="104857600" />

                <!-- Block access to sensitive files -->
                <fileExtensions>
                    <add fileExtension=".env" allowed="false" />
                    <add fileExtension=".yaml" allowed="false" />
                    <add fileExtension=".yml" allowed="false" />
                    <add fileExtension=".ini" allowed="false" />
                    <add fileExtension=".log" allowed="false" />
                    <add fileExtension=".bak" allowed="false" />
                    <add fileExtension=".sql" allowed="false" />
                    <add fileExtension=".git" allowed="false" />
                </fileExtensions>

                <!-- Block hidden segments -->
                <hiddenSegments>
                    <add segment=".git" />
                    <add segment=".env" />
                    <add segment="bin" />
                    <add segment="config" />
                </hiddenSegments>
            </requestFiltering>
        </security>

        <!-- WebSocket Configuration -->
        <webSocket enabled="true" receiveBufferLimit="4194304" />

        <!-- Compression -->
        <urlCompression doStaticCompression="true" doDynamicCompression="true" />
        <httpCompression>
            <dynamicTypes>
                <add mimeType="application/json" enabled="true" />
                <add mimeType="application/javascript" enabled="true" />
            </dynamicTypes>
            <staticTypes>
                <add mimeType="text/css" enabled="true" />
                <add mimeType="application/javascript" enabled="true" />
            </staticTypes>
        </httpCompression>

        <!-- Static Content Caching -->
        <staticContent>
            <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="365.00:00:00" />
            <!-- MIME types for modern web assets -->
            <mimeMap fileExtension=".woff" mimeType="font/woff" />
            <mimeMap fileExtension=".woff2" mimeType="font/woff2" />
            <mimeMap fileExtension=".json" mimeType="application/json" />
        </staticContent>

        <!-- Default Document -->
        <defaultDocument>
            <files>
                <clear />
                <add value="index.html" />
            </files>
        </defaultDocument>

        <!-- Directory Browsing (disabled) -->
        <directoryBrowse enabled="false" />

        <!-- Custom Error Pages -->
        <httpErrors errorMode="Custom" existingResponse="Replace">
            <remove statusCode="404" subStatusCode="-1" />
            <error statusCode="404" path="/404.html" responseMode="ExecuteURL" />
            <remove statusCode="500" subStatusCode="-1" />
            <error statusCode="500" path="/50x.html" responseMode="ExecuteURL" />
            <remove statusCode="502" subStatusCode="-1" />
            <error statusCode="502" path="/50x.html" responseMode="ExecuteURL" />
            <remove statusCode="503" subStatusCode="-1" />
            <error statusCode="503" path="/50x.html" responseMode="ExecuteURL" />
        </httpErrors>
    </system.webServer>
</configuration>
```

### Step 8: Deploy Frontend

Copy Vue 3 build artifacts:

```powershell
# Assuming frontend is built on development machine
# Build command: npm run build (in frontend directory)

# Copy dist folder contents to IIS directory
Copy-Item -Path "path\to\frontend\dist\*" -Destination "C:\inetpub\giljo-mcp" -Recurse -Force

# Set permissions
icacls "C:\inetpub\giljo-mcp" /grant "IIS_IUSRS:(OI)(CI)R"
icacls "C:\inetpub\giljo-mcp" /grant "IUSR:(OI)(CI)R"
```

### Step 9: Configure Windows Firewall

```powershell
# Allow HTTP (will redirect to HTTPS)
New-NetFirewallRule -DisplayName "GiljoAI MCP HTTP" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 80 `
    -Action Allow

# Allow HTTPS
New-NetFirewallRule -DisplayName "GiljoAI MCP HTTPS" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 443 `
    -Action Allow

# Verify rules
Get-NetFirewallRule -DisplayName "GiljoAI*"
```

### Step 10: Application Pool Configuration

**Optimize for production**:

```powershell
# Set recycling to occur at night (2 AM)
Set-ItemProperty "IIS:\AppPools\GiljoAI-MCP-Pool" `
    -Name Recycling.periodicRestart.schedule `
    -Value @{value="02:00:00"}

# Disable idle timeout (keep app always running)
Set-ItemProperty "IIS:\AppPools\GiljoAI-MCP-Pool" `
    -Name processModel.idleTimeout `
    -Value "00:00:00"

# Enable AlwaysRunning
Set-ItemProperty "IIS:\AppPools\GiljoAI-MCP-Pool" `
    -Name startMode `
    -Value "AlwaysRunning"

# Set queue length
Set-ItemProperty "IIS:\AppPools\GiljoAI-MCP-Pool" `
    -Name queueLength `
    -Value 2000

# Disable rapid fail protection (or adjust thresholds)
Set-ItemProperty "IIS:\AppPools\GiljoAI-MCP-Pool" `
    -Name failure.rapidFailProtection `
    -Value $false
```

## Rate Limiting with IIS

IIS does not have built-in rate limiting comparable to nginx. Options:

### Option A: Use DynamicIpRestrictions (Basic)

**web.config addition**:

```xml
<system.webServer>
    <security>
        <dynamicIpSecurity>
            <denyByConcurrentRequests enabled="true" maxConcurrentRequests="20" />
            <denyByRequestRate enabled="true" maxRequests="100" requestIntervalInMilliseconds="60000" />
        </dynamicIpSecurity>
    </security>
</system.webServer>
```

### Option B: Use CloudFlare for Rate Limiting

Recommended for production. CloudFlare provides robust rate limiting.

## Monitoring and Logging

### Enable Failed Request Tracing

```powershell
# Enable failed request tracing
Set-WebConfigurationProperty -Filter "/system.webServer/tracing/traceFailedRequests" `
    -PSPath "IIS:\Sites\GiljoAI-MCP" `
    -Name "enabled" `
    -Value $true

# Add rule to trace 500 errors
Add-WebConfiguration -Filter "/system.webServer/tracing/traceFailedRequests" `
    -PSPath "IIS:\Sites\GiljoAI-MCP" `
    -Value @{
        path="*"
        statusCodes="500-599"
        timeTaken="00:00:00"
    }
```

### Configure IIS Logging

```powershell
# Set log file location
Set-ItemProperty "IIS:\Sites\GiljoAI-MCP" `
    -Name logFile.directory `
    -Value "C:\inetpub\logs\giljo-mcp"

# Log format (W3C Extended)
Set-ItemProperty "IIS:\Sites\GiljoAI-MCP" `
    -Name logFile.logFormat `
    -Value "W3C"

# Enable additional fields
Set-WebConfigurationProperty -Filter "/system.applicationHost/sites/siteDefaults/logFile" `
    -Name "logExtFileFlags" `
    -Value "Date,Time,ClientIP,UserName,Method,UriStem,UriQuery,HttpStatus,TimeTaken,Referer,UserAgent"
```

## Performance Tuning

### Kernel-Mode Caching

```powershell
# Enable kernel-mode caching for static content
Set-WebConfigurationProperty -Filter "/system.webServer/caching" `
    -PSPath "IIS:\Sites\GiljoAI-MCP" `
    -Name "enabled" `
    -Value $true

Set-WebConfigurationProperty -Filter "/system.webServer/caching" `
    -PSPath "IIS:\Sites\GiljoAI-MCP" `
    -Name "enableKernelCache" `
    -Value $true
```

### HTTP/2 Support

HTTP/2 is enabled by default in IIS 10+ on Windows Server 2016+.

Verify:

```powershell
Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\HTTP\Parameters" -Name EnableHttp2Tls
# Should return 1 (enabled)
```

## Security Best Practices

1. **Keep IIS Updated**: Install all Windows updates
2. **Disable Unnecessary Features**: Only enable required IIS features
3. **Use Least Privilege**: App pool runs as minimal privilege account
4. **Enable Request Filtering**: Block malicious requests
5. **Secure Configuration**: Harden `web.config` as shown above
6. **Regular Backups**: Backup IIS configuration
7. **Monitor Logs**: Set up log monitoring and alerting

## Troubleshooting

### WebSocket Not Working

1. Ensure WebSocket protocol is installed:
   ```powershell
   Get-WindowsFeature Web-WebSockets
   # Install if not present:
   Install-WindowsFeature Web-WebSockets
   ```

2. Verify `web.config` has WebSocket enabled:
   ```xml
   <webSocket enabled="true" />
   ```

3. Check ARR proxy settings (timeout must be high)

### 502 Bad Gateway

1. Verify backend is running (localhost:7272)
2. Check ARR proxy is enabled
3. Review IIS logs: `C:\inetpub\logs\LogFiles`
4. Check application event logs

### SSL Certificate Issues

1. Verify certificate is valid and not expired
2. Check certificate binding in IIS Manager
3. Ensure intermediate certificates are installed
4. Test with: `https://www.ssllabs.com/ssltest/`

### Performance Issues

1. Enable output caching for static content
2. Enable compression (gzip/brotli)
3. Increase application pool queue length
4. Monitor with Performance Monitor (perfmon)
5. Consider adding more application instances

## Automated Deployment Script

Save as `deploy-iis.ps1`:

```powershell
# GiljoAI MCP - IIS Automated Deployment Script
param(
    [string]$SiteName = "GiljoAI-MCP",
    [string]$Domain = "yourdomain.com",
    [string]$FrontendPath = "C:\inetpub\giljo-mcp",
    [string]$CertificatePath = "",
    [string]$CertificatePassword = ""
)

# Ensure running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as Administrator"
    exit 1
}

Write-Host "GiljoAI MCP - IIS Deployment" -ForegroundColor Green

# Install required IIS features
Write-Host "Installing IIS features..." -ForegroundColor Yellow
Install-WindowsFeature -name Web-Server, Web-Asp-Net45, Web-Net-Ext45, Web-AppInit, Web-WebSockets -IncludeManagementTools

# Create application pool
Write-Host "Creating application pool..." -ForegroundColor Yellow
New-WebAppPool -Name "$SiteName-Pool" -Force
Set-ItemProperty "IIS:\AppPools\$SiteName-Pool" -Name managedRuntimeVersion -Value ""
Set-ItemProperty "IIS:\AppPools\$SiteName-Pool" -Name startMode -Value "AlwaysRunning"
Set-ItemProperty "IIS:\AppPools\$SiteName-Pool" -Name processModel.idleTimeout -Value "00:00:00"

# Create website directory
Write-Host "Creating website directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $FrontendPath -Force

# Create website
Write-Host "Creating IIS website..." -ForegroundColor Yellow
New-Website -Name $SiteName `
    -PhysicalPath $FrontendPath `
    -ApplicationPool "$SiteName-Pool" `
    -Port 80 `
    -HostHeader $Domain `
    -Force

# Import SSL certificate if provided
if ($CertificatePath -and (Test-Path $CertificatePath)) {
    Write-Host "Importing SSL certificate..." -ForegroundColor Yellow
    $cert = Import-PfxCertificate -FilePath $CertificatePath `
        -CertStoreLocation Cert:\LocalMachine\My `
        -Password (ConvertTo-SecureString -String $CertificatePassword -AsPlainText -Force)

    # Add HTTPS binding
    New-WebBinding -Name $SiteName -Protocol https -Port 443 -HostHeader $Domain
    $binding = Get-WebBinding -Name $SiteName -Protocol https
    $binding.AddSslCertificate($cert.Thumbprint, "My")
}

# Configure firewall
Write-Host "Configuring Windows Firewall..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName "$SiteName HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -Force
New-NetFirewallRule -DisplayName "$SiteName HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow -Force

# Copy web.config template
# (Assumes web.config is in same directory as script)
if (Test-Path ".\web.config") {
    Copy-Item ".\web.config" -Destination $FrontendPath -Force
}

Write-Host "IIS deployment complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Deploy frontend build to: $FrontendPath" -ForegroundColor Cyan
Write-Host "2. Update web.config with your domain" -ForegroundColor Cyan
Write-Host "3. Ensure GiljoAI MCP API is running on localhost:7272" -ForegroundColor Cyan
Write-Host "4. Test: http://$Domain and https://$Domain" -ForegroundColor Cyan
```

Run deployment:

```powershell
.\deploy-iis.ps1 -Domain "yourdomain.com" -CertificatePath "C:\certs\certificate.pfx" -CertificatePassword "your-password"
```

---

## Additional Resources

- IIS Documentation: https://docs.microsoft.com/en-us/iis/
- Application Request Routing: https://www.iis.net/downloads/microsoft/application-request-routing
- URL Rewrite: https://www.iis.net/downloads/microsoft/url-rewrite
- win-acme (Let's Encrypt): https://www.win-acme.com/
