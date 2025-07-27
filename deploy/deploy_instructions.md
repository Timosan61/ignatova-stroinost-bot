# Railway Deployment Instructions

## Quick Deployment Steps

1. **Get Railway API Token**:
   - Go to https://railway.app/account/tokens
   - Create a new token
   - Copy the token

2. **Set Environment Variables**:
   ```bash
   export RAILWAY_TOKEN="your_railway_token_here"
   export BOT_TOKEN="your_telegram_bot_token"
   ```

3. **Run Deployment**:
   ```bash
   python deploy_railway.py
   ```

## Alternative: Using .env file

1. Copy the template:
   ```bash
   cp .env.railway .env
   ```

2. Edit `.env` with your actual values

3. Load environment variables:
   ```bash
   source .env
   python deploy_railway.py
   ```

## What the script does:

1. Creates a new Railway project named "textill-pro-bot"
2. Creates a service within the project
3. Sets up environment variables (BOT_TOKEN, PORT, etc.)
4. Deploys the bot using the existing Dockerfile
5. Provides project/service URLs for monitoring

## Monitoring Deployment

After deployment, you can monitor your bot at:
- Railway Dashboard: https://railway.app/dashboard
- Project-specific URL will be provided after deployment

## Troubleshooting

- Make sure BOT_TOKEN is valid (get from @BotFather)
- Ensure RAILWAY_TOKEN has proper permissions
- Check logs in Railway dashboard if deployment fails