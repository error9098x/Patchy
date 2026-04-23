# Deployment Guide

> Exact steps: local dev → ngrok → optional Render

---

## 1. Local Development (Primary)

### 1.1 First-Time Setup

```bash
# Clone project
cd ~/Desktop/Patchy

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install semgrep filelock PyJWT cryptography

# Verify installs
python3 -c "import flask; print(f'Flask {flask.__version__}')"
semgrep --version
```

### 1.2 Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
# GITHUB_APP_ID, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
# GITHUB_WEBHOOK_SECRET, CEREBRAS_API_KEY, SECRET_KEY
```

### 1.3 Run Server

```bash
# Development mode (auto-reload)
python app.py

# Server starts at http://localhost:5000
# Open in browser: http://localhost:5000
```

---

## 2. ngrok Setup (Required for Webhooks)

### 2.1 Install ngrok

```bash
# macOS
brew install ngrok

# Or download from https://ngrok.com/download
# Sign up for free account to get auth token
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### 2.2 Start Tunnel

```bash
# In separate terminal
ngrok http 5000
```

Output:
```
Forwarding  https://abc123.ngrok-free.app → http://localhost:5000
```

### 2.3 Update GitHub App

1. Go to: https://github.com/settings/apps/YOUR_APP
2. General → Webhook URL → paste ngrok URL + `/webhook`
   - Example: `https://abc123.ngrok-free.app/webhook`
3. Save changes

### 2.4 Verify Webhook

1. Open ngrok inspect: http://127.0.0.1:4040
2. Create test issue comment with @patchy on GitHub
3. Check ngrok inspect UI → should show POST /webhook
4. Check Flask terminal → should show webhook processing log

### Important Notes:
- ngrok URL changes every restart (free plan)
- Update GitHub App webhook URL each time
- Or use `ngrok http 5000 --domain=your-static-domain` ($8/mo)

---

## 3. Optional: Render Deployment

> Only if you need persistent URL. Has constraints.

### 3.1 Limitations
- Free tier: 512MB RAM, spins down after 15min inactivity
- No persistent disk (scans.json resets on deploy)
- Cold start: 30-60s
- Semgrep may OOM on large repos

### 3.2 Setup

```bash
# Create requirements file (already exists)
# Create Procfile
echo "web: gunicorn app:app --bind 0.0.0.0:\$PORT" > Procfile

# Create render.yaml
cat > render.yaml << 'EOF'
services:
  - type: web
    name: patchy
    runtime: python
    buildCommand: pip install -r requirements.txt && pip install semgrep
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT
    envVars:
      - key: GITHUB_APP_ID
        sync: false
      - key: GITHUB_CLIENT_ID
        sync: false
      - key: GITHUB_CLIENT_SECRET
        sync: false
      - key: GITHUB_WEBHOOK_SECRET
        sync: false
      - key: CEREBRAS_API_KEY
        sync: false
      - key: SECRET_KEY
        sync: false
      - key: FLASK_ENV
        value: production
EOF
```

### 3.3 Deploy

1. Push to GitHub
2. Go to render.com → New → Web Service
3. Connect GitHub repo
4. Set environment variables in Render dashboard
5. Deploy

### 3.4 Post-Deploy

1. Copy Render URL (e.g., `https://patchy.onrender.com`)
2. Update GitHub App:
   - Homepage URL → Render URL
   - Callback URL → `https://patchy.onrender.com/callback`
   - Webhook URL → `https://patchy.onrender.com/webhook`

---

## 4. Environment Variables Reference

| Variable | Required | Where to Get |
|----------|----------|-------------|
| `GITHUB_APP_ID` | Yes | GitHub App settings page |
| `GITHUB_APP_PRIVATE_KEY_PATH` | Yes (local) | Download from GitHub App settings |
| `GITHUB_CLIENT_ID` | Yes | GitHub App settings page |
| `GITHUB_CLIENT_SECRET` | Yes | GitHub App settings page |
| `GITHUB_WEBHOOK_SECRET` | Yes | Set during GitHub App creation |
| `CEREBRAS_API_KEY` | Yes | https://cloud.cerebras.ai |
| `SECRET_KEY` | Yes | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | No | `development` or `production` |

---

## 5. Debugging

### Flask not starting
```bash
# Check port in use
lsof -i :5000
# Kill if needed
kill -9 <PID>
```

### Webhooks not received
1. Check ngrok is running: http://127.0.0.1:4040
2. Check GitHub App webhook URL matches ngrok URL
3. Check webhook secret matches between GitHub and .env
4. Check "Recent Deliveries" in GitHub App settings → Advanced

### Semgrep not found
```bash
# Install globally
pip install semgrep
# Or in venv
source venv/bin/activate && pip install semgrep
# Verify
which semgrep
```

### GitHub API errors
```bash
# Check token validity
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.github.com/user
# Check rate limit
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.github.com/rate_limit
```

### Cerebras API errors
```bash
# Test connection
curl https://api.cerebras.ai/v1/models \
  -H "Authorization: Bearer YOUR_KEY"
# Should return model list
```

---

## 6. Pre-Demo Checklist

- [ ] Flask server running on port 5000
- [ ] ngrok tunnel active (if testing webhooks)
- [ ] GitHub App webhook URL updated to ngrok URL
- [ ] .env has all credentials filled
- [ ] Semgrep installed and on PATH
- [ ] Test repo exists with planted vulnerabilities
- [ ] Browser logged out (for clean demo start)
- [ ] Terminal visible for showing logs
- [ ] Screen recording software ready
