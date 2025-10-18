# Create API key for testing
$body = @{username='admin';password='admin'} | ConvertTo-Json
$response = Invoke-WebRequest -Uri 'http://localhost:7272/api/auth/login' -Method Post -ContentType 'application/json' -Body $body -SessionVariable session -UseBasicParsing
Write-Host "Login response:" $response.StatusCode

# Create API key
$body2 = @{name='MCP Test Key';permissions=@('*')} | ConvertTo-Json
$response2 = Invoke-WebRequest -Uri 'http://localhost:7272/api/auth/api-keys' -Method Post -ContentType 'application/json' -Body $body2 -WebSession $session -UseBasicParsing
Write-Host ""
Write-Host "API Key Response:"
$keyData = $response2.Content | ConvertFrom-Json
Write-Host "API Key: $($keyData.api_key)"
Write-Host ""
Write-Host "Set this in your environment:"
Write-Host "`$env:API_KEY = '$($keyData.api_key)'"
