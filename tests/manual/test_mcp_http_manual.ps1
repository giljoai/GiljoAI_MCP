# Manual Integration Tests for MCP-over-HTTP Implementation (Handover 0032)
#
# Prerequisites:
# - Server running on http://localhost:7272
# - Valid API key from database or environment
#
# Usage:
#   $env:API_KEY = "your-api-key-here"
#   .\tests\manual\test_mcp_http_manual.ps1

param(
    [string]$ServerUrl = "http://localhost:7272",
    [string]$ApiKey = $env:API_KEY
)

# Counters
$script:Passed = 0
$script:Failed = 0
$script:Total = 0

# Helper functions
function Write-TestHeader {
    param([string]$Message)
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Test: $Message" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
}

function Assert-StatusCode {
    param(
        [int]$Expected,
        [int]$Actual,
        [string]$TestName
    )

    $script:Total++

    if ($Expected -eq $Actual) {
        Write-Host "✓ PASSED: $TestName (Status: $Actual)" -ForegroundColor Green
        $script:Passed++
        return $true
    } else {
        Write-Host "✗ FAILED: $TestName (Expected: $Expected, Got: $Actual)" -ForegroundColor Red
        $script:Failed++
        return $false
    }
}

function Assert-Contains {
    param(
        [string]$Response,
        [string]$SearchTerm,
        [string]$TestName
    )

    $script:Total++

    if ($Response -match [regex]::Escape($SearchTerm)) {
        Write-Host "✓ PASSED: $TestName (Contains: '$SearchTerm')" -ForegroundColor Green
        $script:Passed++
        return $true
    } else {
        Write-Host "✗ FAILED: $TestName (Missing: '$SearchTerm')" -ForegroundColor Red
        Write-Host "Response: $Response" -ForegroundColor Yellow
        $script:Failed++
        return $false
    }
}

function Write-TestSummary {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Test Summary" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Total Tests: $script:Total"
    Write-Host "Passed: $script:Passed" -ForegroundColor Green
    Write-Host "Failed: $script:Failed" -ForegroundColor Red

    if ($script:Failed -eq 0) {
        Write-Host "All tests passed!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "Some tests failed!" -ForegroundColor Red
        exit 1
    }
}

# Check prerequisites
if ([string]::IsNullOrEmpty($ApiKey)) {
    Write-Host "ERROR: API_KEY not set" -ForegroundColor Red
    Write-Host "Please set your API key: `$env:API_KEY = 'your-api-key-here'"
    exit 1
}

Write-Host "MCP-over-HTTP Integration Tests" -ForegroundColor Cyan
Write-Host "Server: $ServerUrl"
Write-Host "API Key: $($ApiKey.Substring(0, [Math]::Min(12, $ApiKey.Length)))..."
Write-Host ""

# Test 1: Server Health Check
Write-TestHeader "Server Health Check"
try {
    $response = Invoke-WebRequest -Uri "$ServerUrl/health" -Method Get -UseBasicParsing
    Assert-StatusCode -Expected 200 -Actual $response.StatusCode -TestName "Server is running"
    Assert-Contains -Response $response.Content -SearchTerm "healthy" -TestName "Server status is healthy"
} catch {
    Write-Host "✗ FAILED: Server health check - $_" -ForegroundColor Red
    $script:Failed++
}

# Test 2: MCP Endpoint Accessibility (No Auth)
Write-TestHeader "MCP Endpoint Accessibility (Without API Key)"
try {
    $body = @{
        jsonrpc = "2.0"
        method = "initialize"
        params = @{}
        id = 1
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "$ServerUrl/mcp" -Method Post `
        -ContentType "application/json" -Body $body -UseBasicParsing

    Assert-StatusCode -Expected 200 -Actual $response.StatusCode -TestName "MCP endpoint returns 200"
    Assert-Contains -Response $response.Content -SearchTerm "error" -TestName "Response contains error field"
    Assert-Contains -Response $response.Content -SearchTerm "X-API-Key" -TestName "Error mentions missing X-API-Key"
} catch {
    Write-Host "Response: $_" -ForegroundColor Yellow
    $script:Failed++
}

# Test 3: Invalid API Key
Write-TestHeader "Authentication with Invalid API Key"
try {
    $body = @{
        jsonrpc = "2.0"
        method = "initialize"
        params = @{}
        id = 1
    } | ConvertTo-Json

    $headers = @{
        "X-API-Key" = "invalid_key_12345"
    }

    $response = Invoke-WebRequest -Uri "$ServerUrl/mcp" -Method Post `
        -ContentType "application/json" -Body $body -Headers $headers -UseBasicParsing

    Assert-StatusCode -Expected 200 -Actual $response.StatusCode -TestName "Invalid API key returns 200"
    Assert-Contains -Response $response.Content -SearchTerm "error" -TestName "Response contains error"
    Assert-Contains -Response $response.Content -SearchTerm "Invalid API key" -TestName "Error indicates invalid key"
} catch {
    Write-Host "Response: $_" -ForegroundColor Yellow
    $script:Failed++
}

# Test 4: Valid API Key - Initialize Method
Write-TestHeader "Initialize Method (Valid API Key)"
try {
    $body = @{
        jsonrpc = "2.0"
        method = "initialize"
        params = @{
            protocolVersion = "2024-11-05"
            capabilities = @{}
            client_info = @{
                name = "manual-test"
                version = "1.0"
            }
        }
        id = 1
    } | ConvertTo-Json -Depth 10

    $headers = @{
        "X-API-Key" = $ApiKey
    }

    $response = Invoke-WebRequest -Uri "$ServerUrl/mcp" -Method Post `
        -ContentType "application/json" -Body $body -Headers $headers -UseBasicParsing

    Assert-StatusCode -Expected 200 -Actual $response.StatusCode -TestName "Initialize returns 200"
    Assert-Contains -Response $response.Content -SearchTerm '"jsonrpc":"2.0"' -TestName "Response is JSON-RPC 2.0"
    Assert-Contains -Response $response.Content -SearchTerm '"result"' -TestName "Response contains result"
    Assert-Contains -Response $response.Content -SearchTerm '"serverInfo"' -TestName "Result contains serverInfo"
    Assert-Contains -Response $response.Content -SearchTerm '"giljo-mcp"' -TestName "Server name is giljo-mcp"
} catch {
    Write-Host "Response: $_" -ForegroundColor Yellow
    $script:Failed++
}

# Test 5: Tools List Method
Write-TestHeader "Tools List Method"
try {
    $body = @{
        jsonrpc = "2.0"
        method = "tools/list"
        params = @{}
        id = 2
    } | ConvertTo-Json

    $headers = @{
        "X-API-Key" = $ApiKey
    }

    $response = Invoke-WebRequest -Uri "$ServerUrl/mcp" -Method Post `
        -ContentType "application/json" -Body $body -Headers $headers -UseBasicParsing

    Assert-StatusCode -Expected 200 -Actual $response.StatusCode -TestName "Tools list returns 200"
    Assert-Contains -Response $response.Content -SearchTerm '"tools"' -TestName "Result contains tools array"
    Assert-Contains -Response $response.Content -SearchTerm '"name"' -TestName "Tools have name field"
    Assert-Contains -Response $response.Content -SearchTerm '"description"' -TestName "Tools have description field"
} catch {
    Write-Host "Response: $_" -ForegroundColor Yellow
    $script:Failed++
}

# Test 6: Tools Call Method (list_projects)
Write-TestHeader "Tools Call Method (list_projects)"
try {
    $body = @{
        jsonrpc = "2.0"
        method = "tools/call"
        params = @{
            name = "list_projects"
            arguments = @{}
        }
        id = 3
    } | ConvertTo-Json -Depth 10

    $headers = @{
        "X-API-Key" = $ApiKey
    }

    $response = Invoke-WebRequest -Uri "$ServerUrl/mcp" -Method Post `
        -ContentType "application/json" -Body $body -Headers $headers -UseBasicParsing

    Assert-StatusCode -Expected 200 -Actual $response.StatusCode -TestName "Tools call returns 200"
    Assert-Contains -Response $response.Content -SearchTerm '"content"' -TestName "Result contains content"
    Assert-Contains -Response $response.Content -SearchTerm '"type":"text"' -TestName "Content has text type"
} catch {
    Write-Host "Response: $_" -ForegroundColor Yellow
    $script:Failed++
}

# Test 7: Unknown Method
Write-TestHeader "Error Handling - Unknown Method"
try {
    $body = @{
        jsonrpc = "2.0"
        method = "unknown/method"
        params = @{}
        id = 4
    } | ConvertTo-Json

    $headers = @{
        "X-API-Key" = $ApiKey
    }

    $response = Invoke-WebRequest -Uri "$ServerUrl/mcp" -Method Post `
        -ContentType "application/json" -Body $body -Headers $headers -UseBasicParsing

    Assert-StatusCode -Expected 200 -Actual $response.StatusCode -TestName "Unknown method returns 200"
    Assert-Contains -Response $response.Content -SearchTerm '"error"' -TestName "Response contains error"
    Assert-Contains -Response $response.Content -SearchTerm '"-32601"' -TestName "Error code is -32601"
} catch {
    Write-Host "Response: $_" -ForegroundColor Yellow
    $script:Failed++
}

# Test 8: Full MCP Flow
Write-TestHeader "Full MCP Flow - Initialize → Tools List → Tools Call"
try {
    $headers = @{
        "X-API-Key" = $ApiKey
    }

    # Initialize
    $initBody = @{
        jsonrpc = "2.0"
        method = "initialize"
        params = @{
            protocolVersion = "2024-11-05"
            client_info = @{ name = "flow-test"; version = "1.0" }
        }
        id = 100
    } | ConvertTo-Json -Depth 10

    $initResponse = Invoke-WebRequest -Uri "$ServerUrl/mcp" -Method Post `
        -ContentType "application/json" -Body $initBody -Headers $headers -UseBasicParsing

    Assert-Contains -Response $initResponse.Content -SearchTerm '"result"' -TestName "Initialize step succeeds"

    # List tools
    $listBody = @{
        jsonrpc = "2.0"
        method = "tools/list"
        params = @{}
        id = 101
    } | ConvertTo-Json

    $listResponse = Invoke-WebRequest -Uri "$ServerUrl/mcp" -Method Post `
        -ContentType "application/json" -Body $listBody -Headers $headers -UseBasicParsing

    Assert-Contains -Response $listResponse.Content -SearchTerm '"tools"' -TestName "Tools list step succeeds"

    # Call tool
    $callBody = @{
        jsonrpc = "2.0"
        method = "tools/call"
        params = @{
            name = "list_projects"
            arguments = @{}
        }
        id = 102
    } | ConvertTo-Json -Depth 10

    $callResponse = Invoke-WebRequest -Uri "$ServerUrl/mcp" -Method Post `
        -ContentType "application/json" -Body $callBody -Headers $headers -UseBasicParsing

    Assert-Contains -Response $callResponse.Content -SearchTerm '"content"' -TestName "Tools call step succeeds"
} catch {
    Write-Host "Response: $_" -ForegroundColor Yellow
    $script:Failed++
}

# Print summary
Write-TestSummary
