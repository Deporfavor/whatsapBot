#!/bin/bash

# Railway Deployment Script for WhatsApp Pension Bot
# Run this script to deploy your bot to Railway

echo "🚀 Starting Railway deployment for WhatsApp Pension Bot..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Check if user is logged in
if ! railway whoami &> /dev/null; then
    echo "🔐 Please login to Railway..."
    railway login
fi

# Initialize project if not already done
if [ ! -f "railway.toml" ]; then
    echo "📋 Initializing Railway project..."
    railway init
fi

# Set environment variables
echo "⚙️ Setting environment variables..."
echo "Please enter your WhatsApp credentials:"

read -p "WHATSAPP_TOKEN: " whatsapp_token
read -p "PHONE_NUMBER_ID: " phone_number_id
read -p "VERIFY_TOKEN (create a secure password): " verify_token
read -p "COMPANY_NAME: " company_name
read -p "COMPANY_PHONE: " company_phone

# Set variables in Railway
railway variables set WHATSAPP_TOKEN="$whatsapp_token"
railway variables set PHONE_NUMBER_ID="$phone_number_id"
railway variables set VERIFY_TOKEN="$verify_token"
railway variables set COMPANY_NAME="$company_name"
railway variables set COMPANY_PHONE="$company_phone"
railway variables set PORT=8000
railway variables set ENV=production
railway variables set LOG_LEVEL=INFO

echo "✅ Environment variables set successfully!"

# Deploy to Railway
echo "🚀 Deploying to Railway..."
railway up

# Get the deployment URL
deployment_url=$(railway status --json | python3 -c "import sys, json; print(json.load(sys.stdin)['deployments'][0]['url'])" 2>/dev/null || echo "Check Railway dashboard for URL")

echo ""
echo "🎉 Deployment completed!"
echo "📱 Your WhatsApp bot is now live at: $deployment_url"
echo ""
echo "📋 Next Steps:"
echo "1. Go to Meta Developer Console (developers.facebook.com)"
echo "2. Set webhook URL to: $deployment_url/webhook"
echo "3. Set verify token to: $verify_token"
echo "4. Test with: curl $deployment_url/health"
echo ""
echo "🔧 Useful commands:"
echo "• View logs: railway logs"
echo "• Check status: railway status"
echo "• Open dashboard: railway open"
echo "• Update code: railway up"
echo ""
echo "📊 Power BI endpoints:"
echo "• Interactions: $deployment_url/api/powerbi/interactions"
echo "• Tickets: $deployment_url/api/powerbi/tickets"
echo "• Agent Performance: $deployment_url/api/powerbi/agent-performance"
echo "• Analytics: $deployment_url/api/powerbi/conversation-analytics"