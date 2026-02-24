# Caddy Deployment for Mediann

## Prerequisites

- Ubuntu server with ports 80/443 open
- Cloudflare DNS for mediann.dev (for wildcard cert)
- FastAPI running on localhost:8000

## Installation

```bash
# Install Caddy with Cloudflare DNS plugin (required for wildcard certs)
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install caddy

# Build custom Caddy with Cloudflare DNS plugin
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest
xcaddy build --with github.com/caddy-dns/cloudflare
mv caddy /usr/bin/caddy
```

## Migration from Nginx

```bash
# 1. Stop Nginx (cannot coexist on :80/:443)
systemctl stop nginx
systemctl disable nginx

# 2. Set Cloudflare API token
echo 'CF_API_TOKEN=your_cloudflare_api_token' >> /etc/caddy/environment

# 3. Deploy Caddyfile
cp Caddyfile /etc/caddy/Caddyfile

# 4. Start Caddy
systemctl enable caddy
systemctl start caddy

# 5. Verify
curl -I https://mediann.dev
caddy validate --config /etc/caddy/Caddyfile
```

## How it works

### Platform subdomains (*.mediann.dev)

Single wildcard certificate covers all `*.mediann.dev` subdomains.
Obtained via Cloudflare DNS-01 challenge (no per-subdomain action needed).

### Custom domains (e.g. admin.yastvo.com)

1. Tenant adds custom domain via admin panel
2. Tenant configures CNAME: `admin.yastvo.com -> tenants.mediann.dev`
3. On first HTTPS request, Caddy calls `GET http://localhost:8000/internal/domains/check?domain=admin.yastvo.com`
4. FastAPI checks `tenant_domains` table, returns 200 (allowed) or 403 (denied)
5. Caddy obtains Let's Encrypt certificate via HTTP-01 challenge
6. All subsequent requests are served with valid TLS

### Caddy Admin API

Available at `http://localhost:2019` (not publicly exposed).
Used by backend to check certificate status.

```bash
# List certificates
curl http://localhost:2019/pki/ca/local/certificates

# Reload config
caddy reload --config /etc/caddy/Caddyfile
```

## Alternative: certbot for wildcard (without Cloudflare plugin)

If you cannot use the Cloudflare DNS plugin:

```bash
certbot certonly --manual --preferred-challenges dns \
  -d "*.mediann.dev" -d "mediann.dev" \
  --email ssl@mediann.dev --agree-tos
```

Then in Caddyfile replace the `tls` block for `*.mediann.dev`:
```
tls /etc/letsencrypt/live/mediann.dev/fullchain.pem /etc/letsencrypt/live/mediann.dev/privkey.pem
```

Add renewal hook: `/etc/letsencrypt/renewal-hooks/deploy/reload-caddy.sh`
```bash
#!/bin/bash
systemctl reload caddy
```
