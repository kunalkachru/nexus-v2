# Deployment Architecture

Oracle Cloud VM setup, Docker containerization, and CI/CD pipeline.

## Production Deployment (Oracle Cloud)

```mermaid
graph TB
    subgraph "GitHub (kunalkachru/nexus-v2)"
        CODE["Source Code<br/>(master branch)"]
        DOCKER_FILE["Dockerfile<br/>FROM python:3.11<br/>COPY . /app<br/>CMD uvicorn server.app:app :7860"]
    end
    
    subgraph "GitHub Actions CI/CD"
        PUSH["git push origin master"]
        TEST["1. pytest (495 tests)<br/>+ npm browser (16 tests)"]
        BUILD["2. docker build nexus<br/>Push to registry"]
        DEPLOY["3. SSH deploy to Oracle<br/>Docker pull + restart"]
        SMOKE["4. Smoke tests<br/>(5 production checks)"]
        STATUS["Status: ✅ or ❌"]
    end
    
    subgraph "Oracle Cloud — Frankfurt (E2.1.Micro)"
        subgraph "Network Layer"
            IPTABLES["iptables Rules<br/>Port 22: SSH admin<br/>Port 80: HTTP redirect<br/>Port 443: HTTPS<br/>Port 7860: App health only"]
            DNS["duckdns.org DNS<br/>nexus-triage.duckdns.org<br/>→ 92.5.47.239"]
        end
        
        subgraph "SSL/TLS Layer"
            NGINX["nginx Reverse Proxy<br/>Listen: 0.0.0.0:443 (HTTPS)<br/>Redirect 80 → 443<br/>Upstream: 127.0.0.1:7860"]
            CERT["Let's Encrypt Certificate<br/>(Auto-renew via certbot)<br/>Expires: ~90 days"]
        end
        
        subgraph "Application Layer"
            DOCKER["Docker Container: nexus<br/>Image: nexus:latest<br/>EXPOSE 7860<br/>Restart policy: always<br/>Resource limits: 512MB RAM"]
            UVICORN["uvicorn server.app:app<br/>Bind: 0.0.0.0:7860<br/>Workers: 1 (Micro VM)<br/>Health check: /health"]
        end
        
        subgraph "Data Layer"
            VOL["Named Volume: nexus-data<br/>(Docker managed)<br/>Mount point: /app/artifacts<br/>Filesystem: ext4"]
            DB["SQLite Database<br/>artifacts/incidents.json<br/>(SQLite binary format)<br/>Size: ~10-50MB"]
            PACKS["Replica Packs (read-only)<br/>replica_packs/inc001/<br/>replica_packs/inc002/<br/>replica_packs/inc003/<br/>(Mounted from host)"]
        end
        
        subgraph "Utilities"
            LOGS["Container Logs<br/>(stdout to Docker daemon)<br/>Accessible via docker logs"]
            SYSTEMD["systemd Service<br/>(manages docker-compose)<br/>Auto-restart on crash"]
        end
    end
    
    subgraph "Internet"
        USER["👤 Operator Browser<br/>https://nexus-triage.duckdns.org"]
        WEBHOOK["🔗 Datadog Webhook<br/>POST /api/v1/webhooks/datadog"]
    end
    
    subgraph "Secondary: Render"
        RENDER["Render.com Deployment<br/>Demo environment<br/>Ephemeral (sleeps 15min)<br/>https://nexus-uny5.onrender.com"]
    end
    
    %% Flow
    CODE --> DOCKER_FILE
    DOCKER_FILE --> PUSH
    PUSH --> TEST
    TEST --> BUILD
    BUILD --> DEPLOY
    DEPLOY --> STATUS
    
    TEST -->|if ✅| DEPLOY
    TEST -->|if ❌| STATUS
    
    DEPLOY --> DOCKER
    DOCKER --> UVICORN
    NGINX --> DOCKER
    IPTABLES --> NGINX
    DNS --> IPTABLES
    
    UVICORN --> DB
    UVICORN --> PACKS
    
    DB -.->|persists| VOL
    
    USER -->|HTTPS| DNS
    WEBHOOK -->|HTTPS| DNS
    
    RENDER -->|secondary| USER
    
    %% Styling
    classDef cloud fill:#FF9500,stroke:#C97000,color:#fff
    classDef container fill:#0066CC,stroke:#003D99,color:#fff
    classDef network fill:#50C878,stroke:#2D7A4A,color:#fff
    classDef ci fill:#9B59B6,stroke:#6C3A70,color:#fff
    classDef data fill:#FFD700,stroke:#B8860B,color:#000
    
    class DOCKER,UVICORN container
    class NGINX,IPTABLES,DNS network
    class TEST,BUILD,DEPLOY,SMOKE ci
    class DB,PACKS,VOL data
    class NGINX,CERT,DOCKER,UVICORN cloud
```

## Infrastructure Details

### Oracle Cloud VM Specs

| Property | Value |
|----------|-------|
| **Compute Shape** | VM.Standard.E2.1.Micro |
| **vCPUs** | 1 (burstable) |
| **Memory** | 1 GB RAM |
| **Storage** | 50 GB (root volume) |
| **Region** | Frankfurt (eu-frankfurt-1) |
| **OS** | Ubuntu 22.04 LTS |
| **Public IP** | 92.5.47.239 |
| **SSH Key** | ~/Downloads/ssh-key-2026-06-19.key |
| **Cost** | Always-free tier (~$0/month) |

### SSH Access

```bash
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239

# Common tasks:
docker ps                                    # List containers
docker logs nexus -f                        # Follow app logs
docker exec -it nexus /bin/bash            # Shell into container
sudo systemctl status nexus                # Systemd service status
sudo systemctl restart nexus               # Restart service
```

### Docker Setup

**docker-compose.yml** structure:
```yaml
version: '3.9'
services:
  nexus:
    image: nexus:latest
    container_name: nexus
    restart: always
    ports:
      - "7860:7860"  # Exposed to localhost only initially
    volumes:
      - nexus-data:/app/artifacts
      - /path/to/replica_packs:/app/replica_packs:ro
    environment:
      - APP_ENV=production
      - NEXUS_DATABASE_PATH=/app/artifacts/incidents.json
      - NEXUS_ALLOWED_TENANT_IDS=tenant-a,tenant-system
      - NEXUS_FORGE_MODEL_NAME=gpt-4o
      - NEXUS_USE_OPENAI=0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7860/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  nexus-data:
    driver: local
```

### Network Configuration

**nginx config:**
```nginx
server {
    listen 80;
    server_name nexus-triage.duckdns.org;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name nexus-triage.duckdns.org;
    
    ssl_certificate /etc/letsencrypt/live/nexus-triage.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nexus-triage.duckdns.org/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**iptables rules:**
```bash
# Allow SSH, HTTP, HTTPS
sudo iptables -I INPUT 1 -p tcp --dport 22 -j ACCEPT
sudo iptables -I INPUT 2 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 3 -p tcp --dport 443 -j ACCEPT

# Restrict port 7860 to localhost only
sudo iptables -I INPUT -p tcp -s 127.0.0.1 --dport 7860 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 7860 -j DROP
```

### Data Persistence

**Named Volume (`nexus-data`):**
- Managed by Docker
- Location: `/var/lib/docker/volumes/nexus-data/_data`
- Contains: `incidents.json` (SQLite database)
- Survives container restarts
- Survives image updates

**Backup Strategy:**
```bash
# Backup
docker run --rm -v nexus-data:/data -v $(pwd):/backup alpine tar czf /backup/incidents-$(date +%Y%m%d).tar.gz /data

# Restore
tar xzf incidents-20260624.tar.gz -C /var/lib/docker/volumes/nexus-data/_data
docker restart nexus
```

## GitHub Actions CI/CD Pipeline

```mermaid
flowchart TD
    PUSH["Push to master"] --> TEST["Run Tests"]
    TEST -->|❌ Fail| STOP["❌ Pipeline Stops"]
    TEST -->|✅ Pass| BUILD["Build Docker Image"]
    BUILD -->|❌ Fail| STOP
    BUILD -->|✅ Success| DEPLOY["SSH Deploy to Oracle"]
    DEPLOY -->|Command:| SSH["ssh -i key ubuntu@92.5.47.239<br/>docker pull nexus<br/>docker restart nexus"]
    SSH -->|✅| SMOKE["Run Smoke Tests"]
    SMOKE -->|5 checks:| CHECK1["✓ GET /health"]
    SMOKE -->|5 checks:| CHECK2["✓ GET /queue"]
    SMOKE -->|5 checks:| CHECK3["✓ GET /incident?id=..."]
    SMOKE -->|5 checks:| CHECK4["✓ POST /api/v1/incidents/raw-text"]
    SMOKE -->|5 checks:| CHECK5["✓ GET /docs (OpenAPI)"]
    
    CHECK1 --> FINAL{All 5 checks pass?}
    CHECK2 --> FINAL
    CHECK3 --> FINAL
    CHECK4 --> FINAL
    CHECK5 --> FINAL
    
    FINAL -->|✅ Yes| SUCCESS["✅ Deployment Complete"]
    FINAL -->|❌ No| ROLLBACK["Rollback to previous image"]
    ROLLBACK --> ALERT["Alert on-call engineer"]
    
    style SUCCESS fill:#50C878
    style STOP fill:#E74C3C
    style ALERT fill:#F39C12
```

**Workflow File:** `.github/workflows/deploy.yml`

1. **Test Stage** (5 minutes)
   - `pytest tests/ --ignore=tests/test_production_gate3.py -q` → 495 passed
   - `npm run browser:verify` → 16 passed
   - Exit code 0 required to proceed

2. **Build Stage** (3 minutes)
   - `docker build -t nexus:latest .`
   - Push to registry (if applicable)

3. **Deploy Stage** (2 minutes)
   - SSH into Oracle Cloud VM
   - `docker pull nexus:latest`
   - `docker-compose restart nexus`
   - Wait for health check to pass

4. **Smoke Stage** (1 minute)
   - `bash scripts/test-live.sh https://nexus-triage.duckdns.org`
   - 5 endpoint checks must succeed
   - Exit code 0 = deployment succeeded

## Secondary Deployment: Render

```mermaid
graph LR
    PUSH["git push origin master"]
    
    RENDER["Render.com Auto-Deploy<br/>GitHub integration"]
    
    DEPLOYMENT["nexus-uny5.onrender.com<br/>Ephemeral dyno<br/>Sleeps after 15min inactivity"]
    
    PUSH -->|auto-triggered| RENDER
    RENDER -->|deploy| DEPLOYMENT
    
    NOTE["⚠️ Demo only<br/>Data not preserved<br/>Slower cold starts"]
```

---

## Health Checks

**Production Health:**
```bash
curl https://nexus-triage.duckdns.org/health
# Response: {"status": "ok"}

curl https://nexus-triage.duckdns.org/queue
# Response: {"incidents": [...], "total_count": 5, "last_updated": "2026-06-24T..."}
```

**Monitoring:**
- No monitoring system configured (manual checks via curl)
- Logs available via `docker logs nexus`
- Database accessible via `/app/artifacts/incidents.json`

---

## Common Operational Tasks

| Task | Command |
|------|---------|
| Restart app after code update | `docker-compose restart nexus` |
| View recent logs | `docker logs nexus -n 100` |
| Shell into running container | `docker exec -it nexus /bin/bash` |
| Backup database | `docker run --rm -v nexus-data:/data alpine tar cz /data > backup.tar.gz` |
| Check disk usage | `docker system df` |
| Prune old images | `docker image prune -a` |
| Check SSL cert expiry | `curl -v https://nexus-triage.duckdns.org 2>&1 \| grep expire` |
