# LAN Access URLs - GiljoAI MCP Server

**Server Information**
- Server IP: 10.1.0.118
- Subnet: 10.1.0.0/24
- Platform: Windows
- Deployment Mode: server (LAN)
- Configuration Date: 2025-10-05

---

## Access Points

### For Server Machine (Localhost)

**API Server**
- Base URL: http://127.0.0.1:7272
- Health Check: http://127.0.0.1:7272/health
- API Documentation: http://127.0.0.1:7272/docs
- OpenAPI Schema: http://127.0.0.1:7272/openapi.json

**WebSocket**
- WebSocket URL: ws://127.0.0.1:7272/ws
- Real-time Events: ws://127.0.0.1:7272/events

**Frontend Dashboard**
- Dashboard: http://127.0.0.1:7274
- Login: http://127.0.0.1:7274/login
- Projects: http://127.0.0.1:7274/projects
- Agents: http://127.0.0.1:7274/agents

---

### For LAN Clients (Network Access)

**API Server**
- Base URL: http://10.1.0.118:7272
- Health Check: http://10.1.0.118:7272/health
- API Documentation: http://10.1.0.118:7272/docs
- OpenAPI Schema: http://10.1.0.118:7272/openapi.json

**WebSocket**
- WebSocket URL: ws://10.1.0.118:7272/ws
- Real-time Events: ws://10.1.0.118:7272/events

**Frontend Dashboard**
- Dashboard: http://10.1.0.118:7274
- Login: http://10.1.0.118:7274/login
- Projects: http://10.1.0.118:7274/projects
- Agents: http://10.1.0.118:7274/agents

---

## API Authentication

**Server mode requires API key authentication for all API requests.**

### Generated API Key
giljo_lan_XtrYofhJjr0Mw-qQHzA7py9bzVZbMjKaXfnvGjWBK94

### Using the API Key

**HTTP Header Method**
```bash
curl -H "X-API-Key: giljo_lan_XtrYofhJjr0Mw-qQHzA7py9bzVZbMjKaXfnvGjWBK94"      http://10.1.0.118:7272/api/projects
```

**Python Example**
```python
import requests

headers = {
    "X-API-Key": "giljo_lan_XtrYofhJjr0Mw-qQHzA7py9bzVZbMjKaXfnvGjWBK94"
}

response = requests.get("http://10.1.0.118:7272/api/projects", headers=headers)
print(response.json())
```

**JavaScript Example**
```javascript
fetch('http://10.1.0.118:7272/api/projects', {
    headers: {
        'X-API-Key': 'giljo_lan_XtrYofhJjr0Mw-qQHzA7py9bzVZbMjKaXfnvGjWBK94'
    }
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## Quick Health Checks

### From Server Machine
```bash
# Check API is running
curl http://127.0.0.1:7272/health

# Expected response:
# {"status": "healthy", "version": "2.0.0", "mode": "server"}
```

### From LAN Client
```bash
# Check API is accessible
curl http://10.1.0.118:7272/health

# With API key (if configured)
curl -H "X-API-Key: giljo_lan_XtrYofhJjr0Mw-qQHzA7py9bzVZbMjKaXfnvGjWBK94"      http://10.1.0.118:7272/health
```

### Browser Access
1. Open browser
2. Navigate to: http://10.1.0.118:7274
3. Dashboard should load
4. Check browser console for WebSocket connection status

---

## Port Summary

| Service | Port | Protocol | Access |
|---------|------|----------|--------|
| API Server | 7272 | HTTP/WebSocket | LAN + Localhost |
| Frontend | 7274 | HTTP | LAN + Localhost |
| Database | 5432 | PostgreSQL | Localhost ONLY |

---

## Network Configuration

### Firewall Rules
- **GiljoAI MCP API**: Port 7272 TCP (Inbound, Domain/Private profiles)
- **GiljoAI MCP Frontend**: Port 7274 TCP (Inbound, Domain/Private profiles)

### CORS Configuration
Allowed origins:
- http://127.0.0.1:7274
- http://localhost:7274
- http://10.1.0.118:7274
- http://10.1.0.*:7274

### Database Security
- Listen addresses: * (all interfaces)
- Host-based auth: 127.0.0.1/32 and ::1/128 ONLY
- Result: Database accessible from localhost ONLY (secure)

---

## Testing Connectivity

### Test from Server
```bash
# Test API
curl http://127.0.0.1:7272/health

# Test frontend serving
curl -I http://127.0.0.1:7274

# Test database connection
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -d giljo_mcp -c "SELECT 1;"
```

### Test from LAN Client
```bash
# Test API reachability
ping 10.1.0.118

# Test API health
curl http://10.1.0.118:7272/health

# Test API with key
curl -H "X-API-Key: giljo_lan_XtrYofhJjr0Mw-qQHzA7py9bzVZbMjKaXfnvGjWBK94"      http://10.1.0.118:7272/api/projects

# Test frontend
curl -I http://10.1.0.118:7274
```

### Browser Testing
1. From LAN client, open: http://10.1.0.118:7274
2. Open browser DevTools (F12)
3. Check Console tab for WebSocket connection
4. Should see: "WebSocket connected to ws://10.1.0.118:7272"

---

## Troubleshooting

### "Connection refused" from LAN client
1. Verify firewall rules: `netsh advfirewall firewall show rule name="GiljoAI MCP API"`
2. Check API is running: `netstat -an | grep 7272`
3. Verify API bound to 0.0.0.0: `cat config.yaml | grep "host:"`

### CORS errors in browser
1. Check browser is accessing correct URL: http://10.1.0.118:7274
2. Verify CORS config: `cat config.yaml | grep -A5 "cors:"`
3. Check browser console for specific origin being blocked

### "Unauthorized" errors
1. Verify server mode: `cat config.yaml | grep "mode:"`
2. Check API key header: Must be `X-API-Key`
3. Verify API key value matches generated key

### Database connection errors
1. Check PostgreSQL is running
2. Verify credentials in config.yaml
3. Test local connection: `PGPASSWORD=$DB_PASSWORD psql -U postgres -l`

---

## Security Notes

1. **API Key Security**
   - Never commit API keys to git
   - Rotate keys periodically
   - Use environment-specific keys
   - Store in .env file (gitignored)

2. **Network Security**
   - Firewall rules restrict to domain/private networks only
   - Database not exposed to network
   - CORS restricts allowed origins
   - Rate limiting active (60 req/min)

3. **SSL/TLS**
   - Current deployment: HTTP only
   - For production: Configure HTTPS with SSL certificates
   - Self-signed certs acceptable for LAN

---

## Next Steps

1. **Configure API Key** - Add to .env or database
2. **Test from LAN Client** - Verify network accessibility
3. **Security Audit** - Run LAN_SECURITY_CHECKLIST.md
4. **Document for Team** - Share access URLs with team members
5. **Monitor Logs** - Check logs/giljo_mcp.log for errors

---

**Generated**: 2025-10-05  
**Agent**: Network Security Engineer  
**Status**: Configuration Complete - Ready for Testing
