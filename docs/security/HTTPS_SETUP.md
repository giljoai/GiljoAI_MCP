# HTTPS Setup Guide

## Overview

GiljoAI MCP supports optional HTTPS for secure encrypted communication. HTTPS is **not required** for development but **recommended** for production deployments.

**When to Use HTTPS**:
- Production deployments on network or cloud
- When handling sensitive project data
- When browser requires secure context (Service Workers, etc.)

**When HTTP is Fine**:
- Local development (HTTP is faster and easier)

---

## Quick Start: Self-Signed Certificate (Development)

**Step 1: Generate Certificate**
```bash
python scripts/generate_ssl_cert.py
```

This creates:
- `certs/ssl_key.pem` - Private key
- `certs/ssl_cert.pem` - Self-signed certificate (valid 365 days)

It also updates `config.yaml` to enable SSL automatically.

**Step 2: Restart Server**
```bash
python startup.py
```

The server automatically detects certificates in `config.yaml` and starts in HTTPS mode.

**Step 3: Access Dashboard**
```
https://localhost:7274
```

Browser Warning: Self-signed certificates show security warnings. Click "Advanced" > "Proceed to localhost" to continue.

---

## Production Setup: Let's Encrypt (Free CA Certificate)

For production, use Let's Encrypt for trusted certificates.

### Requirements
- Domain name pointing to your server (e.g., `giljoai.example.com`)
- Port 80 open for ACME challenge
- Certbot installed

### Steps

**1. Install Certbot**
```bash
# Ubuntu/Debian
sudo apt-get install certbot

# macOS
brew install certbot
```

**2. Generate Certificate**
```bash
sudo certbot certonly --standalone -d giljoai.example.com
```

**3. Update config.yaml**
```yaml
features:
  ssl_enabled: true

paths:
  ssl_cert: /etc/letsencrypt/live/giljoai.example.com/fullchain.pem
  ssl_key: /etc/letsencrypt/live/giljoai.example.com/privkey.pem
```

**4. Restart Server**
```bash
python startup.py
```

**5. Auto-Renewal**
```bash
sudo certbot renew --dry-run
sudo crontab -e
# Add: 0 0 * * 0 certbot renew --quiet && systemctl restart giljoai-mcp
```

---

## Configuration Reference

### config.yaml SSL Options

```yaml
features:
  ssl_enabled: true

paths:
  ssl_cert: /path/to/certificate.pem
  ssl_key: /path/to/private_key.pem
```

### Command-Line Override

```bash
python api/run_api.py \
  --ssl-keyfile /path/to/key.pem \
  --ssl-certfile /path/to/cert.pem
```

### Environment Variables (Lowest Priority)

```bash
export SSL_CERT_FILE=/path/to/cert.pem
export SSL_KEY_FILE=/path/to/key.pem
python startup.py
```

**Configuration Priority**: CLI args > config.yaml > environment variables

---

## Reverse Proxy Alternative (Nginx)

If you prefer a reverse proxy to handle SSL:

```nginx
server {
    listen 443 ssl;
    server_name giljoai.example.com;

    ssl_certificate /etc/letsencrypt/live/giljoai.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/giljoai.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:7272;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location /ws/ {
        proxy_pass http://localhost:7272;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

In this setup, keep `ssl_enabled: false` in config.yaml since Nginx handles SSL.

---

## Troubleshooting

### Browser Shows "Certificate Invalid"
- **Self-signed**: Expected. Click through the warning for development.
- **Let's Encrypt**: Check expiry with `openssl x509 -in cert.pem -noout -dates`

### WebSocket Connection Fails (wss://)
- Frontend must use `wss://` when HTTPS is enabled
- Check browser console Network tab for mixed content errors

### Server Fails to Start
- Verify certificate paths in config.yaml are absolute
- Check file permissions: `ls -la certs/`
- Verify format: `openssl x509 -in certs/ssl_cert.pem -text -noout`

### Disabling HTTPS
Set `features.ssl_enabled: false` in config.yaml and restart the server.

---

## Security Best Practices

- Never commit private keys to version control (`.gitignore` already covers `certs/`)
- Use restrictive permissions: `chmod 600 certs/ssl_key.pem`
- Use 4096-bit RSA keys (default in generate script)
- For production, always use Let's Encrypt or a trusted CA
