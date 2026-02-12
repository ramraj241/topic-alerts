# Setup Guide

Complete step-by-step guide to set up the AI Learning Agent for Medium.

## Prerequisites

Before starting, ensure you have:

- [ ] Docker Desktop installed ([download](https://www.docker.com/products/docker-desktop/))
- [ ] A Telegram account
- [ ] An OpenAI API key ([get one](https://platform.openai.com/api-keys))
- [ ] Basic terminal/command line knowledge

## Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd ai-learning-agent-for-medium
```

## Step 2: Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Start a chat and send `/newbot`
3. Follow the prompts:
   - Choose a name: `My Learning Agent`
   - Choose a username: `my_learning_agent_bot` (must end in `bot`)
4. **Save the bot token** - you'll need it for the `.env` file

### Get Your Chat ID

1. Search for `@userinfobot` on Telegram
2. Start a chat - it will reply with your user info
3. **Save your Chat ID** (the number, e.g., `123456789`)

### Start Your Bot

1. Search for your new bot by its username
2. Click "Start" or send `/start`
3. This is required for the bot to send you messages

## Step 3: Configure Environment

```bash
# Copy the template
cp .env.example .env

# Edit with your credentials
nano .env  # or use any text editor
```

Fill in these required values:

```env
OPENAI_API_KEY=sk-your-actual-openai-key
TELEGRAM_BOT_TOKEN=123456789:ABCdef...your-bot-token
TELEGRAM_CHAT_ID=your-chat-id-number
```

## Step 4: Start n8n

```bash
# Start the container
docker-compose up -d

# Check it's running
docker-compose ps

# View logs if needed
docker-compose logs -f n8n
```

Wait about 30 seconds for n8n to fully start.

## Step 5: Access n8n

1. Open your browser to `http://localhost:5678`
2. Log in with the credentials from `.env`:
   - Username: `admin` (or your N8N_USER value)
   - Password: your N8N_PASSWORD value

## Step 6: Set Up Credentials in n8n

### OpenAI Credentials

1. In n8n, go to **Settings** â†’ **Credentials**
2. Click **Add Credential**
3. Search for "OpenAI"
4. Enter your API key
5. Click **Save**

### Telegram Credentials

1. Click **Add Credential**
2. Search for "Telegram"
3. Enter your bot token
4. Click **Save**

## Step 7: Import the Workflow

1. Go to **Workflows** in the left menu
2. Click the **...** menu â†’ **Import from File**
3. Select `n8n-workflows/medium-to-audio-workflow.json`
4. Click **Import**

## Step 8: Configure Workflow Nodes

After importing, you need to connect your credentials:

1. **Double-click "AI Simplify Article"** node
   - Under Credential, select your OpenAI credential
   - Click **Save**

2. **Double-click "Text to Speech"** node
   - Select your OpenAI credential
   - Click **Save**

3. **Double-click "Send Audio to Telegram"** node
   - Select your Telegram credential
   - Click **Save**

4. **Double-click "Send Text Summary"** node
   - Select your Telegram credential
   - Click **Save**

## Step 9: Test the Workflow

1. Click **Execute Workflow** (play button)
2. Watch the execution in real-time
3. Check your Telegram for the message

If successful, you'll receive:
- An audio file explaining the article
- A text summary below it

## Step 10: Activate for Daily Runs

1. Toggle the **Active** switch (top right) to ON
2. The workflow will now run daily at 7 AM

## Customization

### Change Schedule Time

1. Click on "Daily 7 AM Trigger" node
2. Change the cron expression:
   - `0 8 * * *` = 8 AM daily
   - `0 7 * * 1-5` = 7 AM weekdays only
   - `0 7,19 * * *` = 7 AM and 7 PM daily

### Add More RSS Feeds

Edit `config/feeds.json` to add sources:

```json
{
  "name": "Your New Feed",
  "url": "https://example.com/feed.xml",
  "enabled": true,
  "priority": 10
}
```

Then update the "Fetch Medium RSS" node URL in n8n.

### Change AI Model

In the "AI Simplify Article" node:
- Change `model` to `gpt-4o` for better quality (more expensive)
- Or use `gpt-3.5-turbo` for lower cost

### Change Voice

In the "Text to Speech" node, options are:
- `nova` - Warm, conversational (default)
- `alloy` - Neutral
- `echo` - Male, clear
- `fable` - Expressive, British
- `onyx` - Deep male
- `shimmer` - Female, friendly

## Troubleshooting

### "No new articles" every day

The workflow tracks processed articles. To reset:

```bash
# Remove the tracking file
docker exec ai-learning-agent-n8n rm /home/node/data/processed_articles.json
```

### Telegram messages not arriving

1. Verify you started your bot (sent `/start`)
2. Check chat ID is correct
3. Test with the utility script:

```bash
python scripts/test_telegram.py YOUR_BOT_TOKEN YOUR_CHAT_ID
```

### Audio file too long

Edit the prompt in "AI Simplify Article" to request shorter output:
- Change "450-500 words" to "300-350 words"

### n8n not starting

```bash
# Check logs
docker-compose logs n8n

# Restart
docker-compose restart n8n

# Full reset
docker-compose down
docker volume rm ai-learning-agent-for-medium_n8n_data
docker-compose up -d
```

## Cost Monitoring

Track your OpenAI usage at https://platform.openai.com/usage

Expected costs:
- GPT-4o-mini: ~$0.003/article
- TTS-1: ~$0.012/article
- **Total: ~$0.50/month** for daily articles

## Step 11: Configure Topic Subscription Webhook

The topic subscribe page needs Telegram webhook delivery to complete `/start subscribe_*` confirmations.

1. Set these values in `.env`:
   - `TELEGRAM_BOT_USERNAME` (without `@`, optional if token is valid)
   - `TELEGRAM_WEBHOOK_SECRET` (optional but recommended)
   - `TELEGRAM_SUBSCRIPTION_TOPICS` (comma-separated topic slugs shown in the form)
   - `TELEGRAM_SUBSCRIPTION_CORS_ORIGINS` (for example `http://localhost:5500`)
   - `TELEGRAM_SUBSCRIPTION_WEBHOOK_URL` (public HTTPS URL ending with `/api/telegram/webhook`)
2. Start the API service:

```bash
docker-compose up -d telegram-subscriptions
```

3. Register webhook with Telegram:

```bash
python scripts/set_telegram_webhook.py
```

4. Verify health:

```bash
curl http://localhost:8200/health
```

For Vercel (same frontend + API domain), verify:

```bash
curl https://your-domain.vercel.app/api/health
```

5. Open `docs/telegram-subscribe.html`, choose a topic, and confirm via Telegram.
   - The page now waits for confirmation and shows success automatically once `/start subscribe_*` is processed by the webhook.

After subscribing, users can manage subscriptions in bot chat:

- `/topics`
- `/unsubscribe <topic>`
- `/unsubscribe_all`

To deliver alerts to topic subscribers from n8n or another service:

```bash
curl -X POST "http://localhost:8200/api/telegram/topics/data-engineering/notify" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"New data-engineering digest is ready\"}"
```

## Vercel same-domain deployment notes

When deploying `services/subscriptions/app.py` on Vercel, do not use local file storage for subscriptions.
Set these environment variables in Vercel:

- `KV_REST_API_URL`
- `KV_REST_API_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME` (optional)
- `TELEGRAM_WEBHOOK_SECRET`
- `TELEGRAM_SUBSCRIPTION_TOPICS`
- `TELEGRAM_SUBSCRIPTION_CORS_ORIGINS=https://topic-alerts.vercel.app`

Webhook URL for Telegram:

`https://topic-alerts.vercel.app/api/telegram/webhook`
