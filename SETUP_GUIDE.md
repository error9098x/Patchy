# Environment Setup Guide

Follow these steps to configure Patchy's environment variables.

---

## Step 1: Generate Flask Secret Key (1 min)

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and save it for later.

---

## Step 2: Register GitHub App (5 min)

### 2.1 Go to GitHub App Registration
Visit: https://github.com/settings/apps/new

### 2.2 Fill in Basic Information
- **GitHub App name**: `Patchy` (or `Patchy-YourUsername` if taken)
- **Homepage URL**: `http://localhost:5001`
- **Callback URL**: `http://localhost:5001/callback`
- **Setup URL**: Leave empty
- **Webhook URL**: `https://placeholder.ngrok.io/webhook` (we'll update this later)
- **Webhook secret**: Generate with:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
  Copy and paste the output

### 2.3 Set Permissions
Under "Repository permissions":
- **Contents**: Read & Write
- **Pull requests**: Read & Write
- **Issues**: Read & Write
- **Metadata**: Read-only

### 2.4 Subscribe to Events
Check these boxes:
- ✅ Issue comment
- ✅ Pull request

### 2.5 Where can this GitHub App be installed?

**For Development/Testing (Choose this now)**:
- Select: **Only on this account**

**Why "Only on this account" for now**:
- ✅ Safer for development (localhost + ngrok)
- ✅ Easier debugging (only your repos affected)
- ✅ No risk to other users during testing
- ✅ Can test all features on your own repos

**When to switch to "Any account"**:
- ✅ When deploying to production (Railway/Vercel)
- ✅ When you have a stable public domain
- ✅ When webhook endpoint is reliable
- ✅ When ready for real users

**Note**: You'll create a **separate production app** later with "Any account" when deploying. This dev app stays for testing.

See: [Production Deployment Strategy](#production-deployment-strategy) below.

### 2.6 Create the App
Click **"Create GitHub App"**

### 2.7 Note Down Values
After creation, you'll see:
- **App ID** - Copy this
- **Client ID** - Copy this
- **Client secrets** - Click "Generate a new client secret" and copy it

### 2.8 Generate Private Key
Scroll down to "Private keys" section:
- Click **"Generate a private key"**
- A `.pem` file will download
- Move it to your project root and rename to `github-app-key.pem`:
  ```bash
  mv ~/Downloads/patchy-*.private-key.pem ./github-app-key.pem
  ```

---

## Step 3: Get Cerebras API Key (3 min)

### 3.1 Sign Up
Visit: https://cloud.cerebras.ai

### 3.2 Create Account
- Sign up with email or GitHub
- Verify email if needed

### 3.3 Generate API Key
- Go to API Keys section
- Click "Create API Key"
- Copy the key (starts with `csk-...`)

---

## Step 4: Create .env File (2 min)

```bash
# Copy the example file
cp .env.example .env

# Open in your editor
nano .env
# or
code .env
```

Fill in all the values:

```bash
# GitHub App
GITHUB_APP_ID=123456                                    # From Step 2.7
GITHUB_CLIENT_ID=Iv1.abc123def456                      # From Step 2.7
GITHUB_CLIENT_SECRET=ghp_abc123def456...               # From Step 2.7
GITHUB_WEBHOOK_SECRET=abc123def456...                  # From Step 2.2
GITHUB_APP_PRIVATE_KEY_PATH=./github-app-key.pem       # From Step 2.8

# Cerebras API
CEREBRAS_API_KEY=csk-abc123def456...                   # From Step 3.3

# Flask
SECRET_KEY=abc123def456...                             # From Step 1
FLASK_ENV=development
FLASK_DEBUG=1

# Redis (leave as-is for local development)
REDIS_URL=redis://localhost:6379

# Server
PORT=5001
```

Save and close the file.

---

## Step 5: Verify Setup (2 min)

### 5.1 Check .env File Exists
```bash
ls -la .env
```
Should show the file (not in git)

### 5.2 Check Private Key Exists
```bash
ls -la github-app-key.pem
```
Should show the .pem file (not in git)

### 5.3 Test Cerebras Connection
```bash
python3 tools/cerebras_client.py
```

Expected output:
```
Testing Cerebras connection...
✅ Connection successful!

Testing streaming:
1, 2, 3, 4, 5
```

If you see errors:
- ❌ `ModuleNotFoundError: No module named 'cerebras'` → Run `pip install cerebras-cloud-sdk`
- ❌ `Authentication failed` → Check your `CEREBRAS_API_KEY` in .env
- ❌ `Connection refused` → Check your internet connection

---

## Step 6: Install GitHub App on Your Account (2 min)

### 6.1 Go to App Settings
Visit: https://github.com/settings/apps

### 6.2 Click on Your App
Click "Patchy" (or whatever you named it)

### 6.3 Install App
- Click "Install App" in the left sidebar
- Select your account
- Choose repositories:
  - **Option A**: All repositories (not recommended)
  - **Option B**: Only select repositories (recommended)
    - Select a test repo or create a new one for testing
- Click "Install"

### 6.4 Note Installation ID (Optional)
After installation, the URL will be:
```
https://github.com/settings/installations/12345678
```
The number `12345678` is your installation ID (you don't need to save this, the app will fetch it automatically)

---

## Step 7: Setup ngrok for Webhooks (Optional - for issue responder)

### 7.1 Install ngrok
```bash
# macOS
brew install ngrok

# Or download from https://ngrok.com/download
```

### 7.2 Start ngrok
```bash
ngrok http 5001
```

### 7.3 Copy the HTTPS URL
You'll see something like:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:5001
```

Copy the `https://abc123.ngrok.io` URL

### 7.4 Update GitHub App Webhook URL
- Go to: https://github.com/settings/apps
- Click your app
- Update "Webhook URL" to: `https://abc123.ngrok.io/webhook`
- Click "Save changes"

**Note**: ngrok URL changes every time you restart it. You'll need to update the webhook URL each time.

---

## Verification Checklist

Before proceeding, verify:

- [ ] `.env` file exists and has all values filled
- [ ] `github-app-key.pem` exists in project root
- [ ] `.env` and `*.pem` are in `.gitignore` (not committed to git)
- [ ] Cerebras connection test passes
- [ ] GitHub App is installed on at least one repository
- [ ] (Optional) ngrok is running and webhook URL is updated

---

## Troubleshooting

### "Permission denied" when reading .pem file
```bash
chmod 600 github-app-key.pem
```

### "Module not found" errors
```bash
pip install -r requirements.txt
pip install cerebras-cloud-sdk semgrep
```

### Can't access GitHub App settings
Make sure you're logged into the GitHub account that created the app.

### Webhook not receiving events
- Check ngrok is running
- Check webhook URL in GitHub App settings matches ngrok URL
- Check webhook secret matches in .env

---

## Security Notes

⚠️ **Never commit these files to git**:
- `.env`
- `github-app-key.pem`
- Any file containing API keys or secrets

✅ **Safe to commit**:
- `.env.example` (template with no real values)
- `.gitignore` (protects sensitive files)

---

## Next Steps

Once setup is complete, you can:
1. Start the Flask server: `flask run --port 5001`
2. Visit: http://localhost:5001
3. Test GitHub login
4. Begin implementing agents

---

## Production Deployment Strategy

### Development App vs Production App

**Current Setup (Development)**:
- App name: `Patchy` or `Patchy-Dev`
- Installation: "Only on this account"
- Webhook: ngrok URL (changes every restart)
- Purpose: Testing and development

**Future Setup (Production)**:
- App name: `Patchy` (official)
- Installation: **"Any account"** ✅
- Webhook: Stable domain (e.g., `https://patchy.app/webhook`)
- Purpose: Public use by anyone

### When to Create Production App

Create a separate production GitHub App when:
1. ✅ Code is tested and stable
2. ✅ Deployed to Railway/Vercel with custom domain
3. ✅ Webhook endpoint is reliable (not ngrok)
4. ✅ Ready for users to install on their repos
5. ✅ Privacy policy and terms of service ready

### How to Create Production App

1. **Keep dev app** for testing
2. **Create new app** at https://github.com/settings/apps/new
3. **Use same settings** but change:
   - Name: `Patchy` (official name)
   - Homepage: `https://patchy.app`
   - Webhook: `https://patchy.app/webhook`
   - Installation: **"Any account"** ✅
4. **Update production .env** with new credentials
5. **Deploy to Railway** with production app credentials

### Two-App Strategy Benefits

**Development App**:
- Test new features safely
- Debug on your repos only
- Use ngrok for local testing
- Break things without affecting users

**Production App**:
- Stable for real users
- Monitored and reliable
- Professional domain
- Public marketplace listing

### Migration Checklist

When ready for production:
- [ ] Code tested thoroughly
- [ ] Deployed to Railway with custom domain
- [ ] Create production GitHub App
- [ ] Update production .env
- [ ] Test production app on test repo
- [ ] Announce to users
- [ ] Keep dev app for future testing

---

**Setup complete!** 🎉
