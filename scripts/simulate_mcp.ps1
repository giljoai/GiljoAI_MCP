Param(
  [string]$ServerUrl = 'http://10.1.0.164:7272',
  [string]$TenantKey = 'tk_eHuGt1LnLvWGxSnQURqvSjEhfluWNxD0',
  [string]$ProjectId = 'ce9015f5-d521-449c-9a89-66a9055436c8',
  [string]$Mission = 'Hello World – Simulated via PowerShell',
  [switch]$AlsoCreateAgent
)

# Small helper to POST JSON with sensible defaults
function Invoke-JsonPost {
  param(
    [Parameter(Mandatory=$true)][string]$Uri,
    [Parameter(Mandatory=$true)][hashtable]$Body
  )
  $json = $Body | ConvertTo-Json -Depth 6
  try {
    $resp = Invoke-RestMethod -Method Post -Uri $Uri -ContentType 'application/json' -Body $json -TimeoutSec 10
    return $resp
  }
  catch {
    Write-Warning ("Request to {0} failed: {1}" -f $Uri, $_.Exception.Message)
    if ($_.ErrorDetails) { Write-Warning $_.ErrorDetails }
    throw
  }
}

# Bridge endpoint removed in 0765a — all lines below are commented out.
# The /api/v1/ws-bridge/emit endpoint no longer exists; events are emitted
# via in-process WebSocketManager.

# $bridge = "$ServerUrl/api/v1/ws-bridge/emit"
#
# Write-Host "[SIM] Posting project:mission_updated to $bridge" -ForegroundColor Cyan
#
# $missionBody = @{
#   event_type = 'project:mission_updated'
#   tenant_key = $TenantKey
#   data = @{
#     project_id = $ProjectId
#     mission = $Mission
#     user_config_applied = $false
#     token_estimate = $Mission.Length
#     generated_by = 'orchestrator'
#   }
# }
#
# $missionResp = Invoke-JsonPost -Uri $bridge -Body $missionBody
# Write-Host ("[SIM] mission_updated result: success={0}, clients_notified={1}" -f $missionResp.success, $missionResp.clients_notified) -ForegroundColor Green
#
# if ($AlsoCreateAgent) {
#   Start-Sleep -Milliseconds 300
#   $agentId = [Guid]::NewGuid().ToString()
#   Write-Host "[SIM] Posting agent:created (job_id=$agentId)" -ForegroundColor Cyan
#
#   $agentBody = @{
#     event_type = 'agent:created'
#     tenant_key = $TenantKey
#     data = @{
#       project_id = $ProjectId
#       agent = @{
#         job_id = $agentId
#         agent_type = 'implementer'
#         agent_name = 'Implementer #PS'
#         status = 'pending'
#       }
#     }
#   }
#
#   $agentResp = Invoke-JsonPost -Uri $bridge -Body $agentBody
#   Write-Host ("[SIM] agent:created result: success={0}, clients_notified={1}" -f $agentResp.success, $agentResp.clients_notified) -ForegroundColor Green
# }
#
# Write-Host "[SIM] Done. Check the project page for real-time updates." -ForegroundColor Yellow

Write-Host "[SIM] simulate_mcp.ps1: Bridge endpoint removed. Script is a no-op." -ForegroundColor Yellow

