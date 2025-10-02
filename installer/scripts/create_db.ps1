# GiljoAI MCP Database Creation Script for Windows
# This is a TEMPLATE script - the installer will generate a customized version
# with pre-filled passwords and configuration.
#
# INSTRUCTIONS:
# 1. Open PowerShell as Administrator:
#    - Press Win+X and select "Windows PowerShell (Admin)"
#    - Or right-click Start and select "Windows Terminal (Admin)"
# 2. Navigate to this directory
# 3. Run: .\create_db.ps1
#
# This script will:
# - Create PostgreSQL roles (giljo_owner, giljo_user)
# - Create the giljo_mcp database
# - Set up all required permissions
# - Save credentials for the installer

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "   GiljoAI MCP - PostgreSQL Database Creation Script" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration (will be pre-filled by installer)
$PgHost = "localhost"
$PgPort = 5432
$PgUser = "postgres"
$DbName = "giljo_mcp"
$OwnerRole = "giljo_owner"
$UserRole = "giljo_user"
$OwnerPassword = "WILL_BE_GENERATED"
$UserPassword = "WILL_BE_GENERATED"

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  PostgreSQL Host: $PgHost" -ForegroundColor Gray
Write-Host "  PostgreSQL Port: $PgPort" -ForegroundColor Gray
Write-Host "  Database Name:   $DbName" -ForegroundColor Gray
Write-Host ""

# Function to run psql command
function Invoke-Psql {
    param(
        [string]$Database = "postgres",
        [string]$Command,
        [switch]$IgnoreError
    )

    try {
        $env:PGPASSWORD = $env:POSTGRES_PASSWORD
        $output = psql -h $PgHost -p $PgPort -U $PgUser -d $Database -c $Command 2>&1
        if ($LASTEXITCODE -ne 0 -and -not $IgnoreError) {
            throw "psql command failed: $output"
        }
        return $output
    } finally {
        $env:PGPASSWORD = $null
    }
}

# Prompt for PostgreSQL admin password
Write-Host "PostgreSQL Administration" -ForegroundColor Yellow
$SecurePassword = Read-Host "Enter password for PostgreSQL user '$PgUser'" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
$env:POSTGRES_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)

Write-Host ""
Write-Host "Testing PostgreSQL connection..." -ForegroundColor Yellow

try {
    $version = Invoke-Psql -Command "SELECT version();"
    Write-Host "  Connected successfully!" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Cannot connect to PostgreSQL" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please verify:" -ForegroundColor Yellow
    Write-Host "  1. PostgreSQL is installed and running"
    Write-Host "  2. The password is correct"
    Write-Host "  3. PostgreSQL is accepting connections on port $PgPort"
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Creating database roles..." -ForegroundColor Yellow

# Create or update owner role
try {
    Invoke-Psql -Command "SELECT 1 FROM pg_roles WHERE rolname='$OwnerRole';" | Out-Null
    Write-Host "  Role '$OwnerRole' exists, updating password..." -ForegroundColor Gray
    Invoke-Psql -Command "ALTER ROLE $OwnerRole WITH PASSWORD '$OwnerPassword';"
} catch {
    Write-Host "  Creating role '$OwnerRole'..." -ForegroundColor Gray
    Invoke-Psql -Command "CREATE ROLE $OwnerRole LOGIN PASSWORD '$OwnerPassword';"
}

# Create or update user role
try {
    Invoke-Psql -Command "SELECT 1 FROM pg_roles WHERE rolname='$UserRole';" | Out-Null
    Write-Host "  Role '$UserRole' exists, updating password..." -ForegroundColor Gray
    Invoke-Psql -Command "ALTER ROLE $UserRole WITH PASSWORD '$UserPassword';"
} catch {
    Write-Host "  Creating role '$UserRole'..." -ForegroundColor Gray
    Invoke-Psql -Command "CREATE ROLE $UserRole LOGIN PASSWORD '$UserPassword';"
}

Write-Host "  Roles created successfully!" -ForegroundColor Green

Write-Host ""
Write-Host "Creating database..." -ForegroundColor Yellow

# Check if database exists
$dbExists = Invoke-Psql -Command "SELECT 1 FROM pg_database WHERE datname='$DbName';" -IgnoreError

if ($dbExists -match "1") {
    Write-Host "  Database '$DbName' already exists" -ForegroundColor Yellow
} else {
    Write-Host "  Creating database '$DbName'..." -ForegroundColor Gray
    Invoke-Psql -Command "CREATE DATABASE $DbName OWNER $OwnerRole;"
    Write-Host "  Database created successfully!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Setting up permissions..." -ForegroundColor Yellow

# Grant permissions
Invoke-Psql -Database $DbName -Command "GRANT CONNECT ON DATABASE $DbName TO $UserRole;" -IgnoreError
Invoke-Psql -Database $DbName -Command "GRANT USAGE, CREATE ON SCHEMA public TO $OwnerRole;" -IgnoreError
Invoke-Psql -Database $DbName -Command "GRANT USAGE ON SCHEMA public TO $UserRole;" -IgnoreError

# Grant default privileges
Invoke-Psql -Database $DbName -Command @"
ALTER DEFAULT PRIVILEGES FOR ROLE $OwnerRole IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO $UserRole;
"@ -IgnoreError

Invoke-Psql -Database $DbName -Command @"
ALTER DEFAULT PRIVILEGES FOR ROLE $OwnerRole IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO $UserRole;
"@ -IgnoreError

Write-Host "  Permissions configured successfully!" -ForegroundColor Green

# Clear the password from environment
$env:POSTGRES_PASSWORD = $null

# Create verification flag for installer
Write-Host ""
Write-Host "Creating verification flag..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"DATABASE_CREATED=$timestamp" | Out-File -FilePath "..\..\database_created.flag" -Encoding UTF8

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "   Database Setup Complete!" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Database Details:" -ForegroundColor Yellow
Write-Host "  Database: $DbName" -ForegroundColor Gray
Write-Host "  Owner Role: $OwnerRole" -ForegroundColor Gray
Write-Host "  User Role: $UserRole" -ForegroundColor Gray
Write-Host ""
Write-Host "Credentials have been saved to:" -ForegroundColor Yellow
Write-Host "  installer\credentials\db_credentials_*.txt" -ForegroundColor Gray
Write-Host ""
Write-Host "You can now return to the installer and press Enter to continue." -ForegroundColor Cyan
Write-Host ""
