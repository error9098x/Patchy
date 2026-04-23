#!/bin/bash
# Patchy Setup Script
# Automates environment configuration

set -e

echo "🛡️  Patchy Setup Script"
echo "======================="
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Copy template
echo "📝 Creating .env file from template..."
cp .env.example .env

# Generate Flask secret key
echo "🔑 Generating Flask SECRET_KEY..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
sed -i.bak "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env && rm .env.bak

echo "✅ Flask SECRET_KEY generated"
echo ""

# Prompt for GitHub App credentials
echo "📱 GitHub App Configuration"
echo "Register at: https://github.com/settings/apps/new"
echo ""

read -p "GitHub App ID: " GITHUB_APP_ID
read -p "GitHub Client ID: " GITHUB_CLIENT_ID
read -p "GitHub Client Secret: " GITHUB_CLIENT_SECRET

# Generate webhook secret
echo ""
echo "🔐 Generating GitHub Webhook Secret..."
WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "Generated: $WEBHOOK_SECRET"
echo "⚠️  Copy this and paste it when registering your GitHub App!"
echo ""

# Update .env with GitHub values
sed -i.bak "s/GITHUB_APP_ID=.*/GITHUB_APP_ID=$GITHUB_APP_ID/" .env && rm .env.bak
sed -i.bak "s/GITHUB_CLIENT_ID=.*/GITHUB_CLIENT_ID=$GITHUB_CLIENT_ID/" .env && rm .env.bak
sed -i.bak "s/GITHUB_CLIENT_SECRET=.*/GITHUB_CLIENT_SECRET=$GITHUB_CLIENT_SECRET/" .env && rm .env.bak
sed -i.bak "s/GITHUB_WEBHOOK_SECRET=.*/GITHUB_WEBHOOK_SECRET=$WEBHOOK_SECRET/" .env && rm .env.bak

echo "✅ GitHub App credentials saved"
echo ""

# Check for private key
echo "🔑 GitHub App Private Key"
if [ -f github-app-key.pem ]; then
    echo "✅ github-app-key.pem found"
else
    echo "⚠️  github-app-key.pem not found!"
    echo "Download it from your GitHub App settings and place it in this directory."
    echo "Then rename it to: github-app-key.pem"
fi
echo ""

# Prompt for Cerebras API key
echo "🧠 Cerebras API Configuration"
echo "Get your API key from: https://cloud.cerebras.ai"
echo ""
read -p "Cerebras API Key: " CEREBRAS_API_KEY

sed -i.bak "s/CEREBRAS_API_KEY=.*/CEREBRAS_API_KEY=$CEREBRAS_API_KEY/" .env && rm .env.bak

echo "✅ Cerebras API key saved"
echo ""

# Test Cerebras connection
echo "🧪 Testing Cerebras connection..."
if python3 -c "
import os
os.environ['CEREBRAS_API_KEY'] = '$CEREBRAS_API_KEY'
from tools.cerebras_client import test_connection
if test_connection():
    print('✅ Cerebras connection successful!')
    exit(0)
else:
    print('❌ Cerebras connection failed!')
    exit(1)
" 2>/dev/null; then
    echo ""
else
    echo "⚠️  Connection test failed. Check your API key."
    echo ""
fi

# Summary
echo "📋 Setup Summary"
echo "================"
echo "✅ .env file created"
echo "✅ Flask SECRET_KEY generated"
echo "✅ GitHub App credentials configured"
echo "✅ Cerebras API key configured"
echo ""

if [ ! -f github-app-key.pem ]; then
    echo "⚠️  TODO: Download and place github-app-key.pem in project root"
    echo ""
fi

echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Install dependencies: pip install -r requirements.txt"
echo "2. Install Semgrep: pip install semgrep"
echo "3. Start server: flask run --port 5001"
echo ""
echo "For detailed instructions, see SETUP_GUIDE.md"
