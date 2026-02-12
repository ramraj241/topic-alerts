# AI Learning Agent for Medium

Automated pipeline that transforms Medium Data Engineering articles into beginner-friendly audio explanations, delivered daily via Telegram.

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Medium RSS     â”‚â”€â”€â”€â”€â–¶â”‚  AI Simplifier  â”‚â”€â”€â”€â”€â–¶â”‚  Text-to-Speech â”‚â”€â”€â”€â”€â–¶â”‚  Telegram Bot   â”‚
â”‚  (Data Eng)     â”‚     â”‚  (Claude/GPT)   â”‚     â”‚  (OpenAI TTS)   â”‚     â”‚  (Daily 7 AM)   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Features

- **RSS Fetching**: Pulls latest articles from Medium Data Engineering feeds
- **AI Simplification**: Converts complex content to beginner-friendly explanations
- **Audio Generation**: Creates natural-sounding speech (3 min max)
- **Telegram Delivery**: Sends audio + summary to your chat daily
- **Duplicate Detection**: Tracks processed articles to avoid repeats

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| Orchestration | n8n (self-hosted) | Free |
| AI | OpenAI GPT-4o-mini / Claude Haiku | ~$0.01/article |
| TTS | OpenAI TTS-1 | ~$0.015/article |
| Delivery | Telegram Bot API | Free |
| Hosting | Docker / Railway / Local | Free-$5/mo |

**Estimated cost**: ~$1-2/month for daily articles

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Telegram account
- OpenAI API key (or Anthropic)

### 2. Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd ai-learning-agent-for-medium

# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env

# Start n8n
docker-compose up -d
```

### 3. Configure Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow prompts
3. Copy the bot token to `.env`
4. Get your chat ID by messaging [@userinfobot](https://t.me/userinfobot)

### 4. Import n8n Workflow

1. Open n8n at `http://localhost:5678`
2. Go to Workflows â†’ Import from File
3. Select `n8n-workflows/medium-to-audio-workflow.json`
4. Configure credentials (OpenAI, Telegram)
5. Activate the workflow

## Configuration

### Environment Variables

See `.env.example` for all options:

- `OPENAI_API_KEY` - For AI simplification and TTS
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `TELEGRAM_CHAT_ID` - Your personal chat ID
- `SCHEDULE_CRON` - When to run (default: 7 AM daily)

### Customizing the Prompt

Edit `templates/explanation_prompt.txt` to adjust:
- Explanation style
- Target duration
- Focus areas

### Adding More RSS Feeds

Edit `config/feeds.json` to add sources:
- Medium publications
- Substack newsletters
- YouTube RSS feeds

## Project Structure

```
ai-learning-agent-for-medium/
â”œâ”€â”€ docker-compose.yml      # n8n container setup
â”œâ”€â”€ .env.example            # Environment template
â”œâ”€â”€ config/
â”‚   â”œâ”€â”€ feeds.json          # RSS feed sources
â”‚   â””â”€â”€ settings.json       # App configuration
â”œâ”€â”€ n8n-workflows/
â”‚   â””â”€â”€ medium-to-audio-workflow.json
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ fetch_article.py    # Custom article parser
â”‚   â””â”€â”€ test_telegram.py    # Bot testing utility
â”œâ”€â”€ templates/
â”‚   â””â”€â”€ explanation_prompt.txt
â””â”€â”€ docs/
    â””â”€â”€ setup-guide.md
```

## Workflow Details

### Pipeline Steps

1. **Schedule Trigger** - Runs daily at configured time
2. **Fetch RSS** - Gets latest articles from Medium
3. **Filter New** - Skips already-processed articles
4. **Extract Content** - Parses full article text
5. **AI Simplify** - Generates beginner-friendly explanation
6. **Text-to-Speech** - Converts to audio file
7. **Send Telegram** - Delivers audio + text summary
8. **Log Processed** - Records article to avoid duplicates

### Error Handling

- Retries on API failures (3 attempts)
- Fallback to next article if one fails
- Daily summary of processed/failed articles

## Cost Breakdown

| Operation | Cost per Article |
|-----------|-----------------|
| GPT-4o-mini (1500 tokens) | ~$0.003 |
| OpenAI TTS-1 (750 words) | ~$0.012 |
| **Total** | ~$0.015 |

Monthly (30 articles): **~$0.50**

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No audio received | Check Telegram bot token and chat ID |
| Empty articles | Medium may block scraping; try different feeds |
| TTS too long | Reduce max explanation length in prompt |
| n8n not starting | Check Docker logs: `docker-compose logs n8n` |

## License

MIT - Use freely for personal learning.

## Telegram Topic Subscriptions

This repo now includes an API service for per-topic Telegram subscriptions.

### What it provides

- `POST /api/telegram/subscribe` - creates a one-time deep link for a topic.
- `GET /api/telegram/subscribe/{start_param}/status` - checks whether the Telegram `/start` confirmation completed.
- `POST /api/telegram/webhook` - receives Telegram updates and confirms subscriptions.
- `GET /api/telegram/topics` - lists topics shown in the subscribe form.
- `GET /api/telegram/topics/{topic}/chat-ids` - returns chat IDs subscribed to a topic.
- `POST /api/telegram/topics/{topic}/notify` - sends an alert (text/audio) to all subscribers for a topic.
- `GET /api/telegram/subscriptions` - inspect stored subscriptions.

### Start the service

`docker-compose up -d telegram-subscriptions`

By default, the API is available at `http://localhost:8200`.

### Configure webhook

Telegram requires a public HTTPS webhook URL. Set `TELEGRAM_SUBSCRIPTION_WEBHOOK_URL` in `.env`, then run:

`python scripts/set_telegram_webhook.py`

### Data storage

Subscription state is persisted in `data/subscriptions/`:

- `pending_subscriptions.json`
- `subscriptions.json`

For serverless deployments (like Vercel), set `KV_REST_API_URL` and `KV_REST_API_TOKEN` to use persistent Redis storage (Upstash/Vercel KV) instead of local files.

### Bot commands for subscribers

- `/topics` - list active topic subscriptions.
- `/unsubscribe <topic>` - remove one topic.
- `/unsubscribe_all` - remove all topic subscriptions.

### Browser flow behavior

`docs/telegram-subscribe.html` now polls the status endpoint after opening Telegram and shows a success message as soon as the user taps **Start** in the bot.

### Triggering topic delivery from your workflow

Call this endpoint after generating your summary/audio:

`POST http://localhost:8200/api/telegram/topics/<topic>/notify`

The included workflow file now has a `Notify Topic Subscribers` HTTP node that posts to:
`http://telegram-subscriptions:8200/api/telegram/topics/data-engineering/notify`
Update the topic slug in that node if you run separate workflows per topic.

Example payload:

```json
{
  "text": "New article: Building reliable Airflow DAGs...",
  "audio_url": "https://your-public-host/audio/airflow-2026-02-12.mp3",
  "caption": "3-minute explanation",
  "disable_web_page_preview": true
}
```

### Deploying Frontend + API on the same Vercel domain

This repo includes Vercel Python function entrypoints:

- `api/index.py`
- `api/[...all].py`

Set these Vercel environment variables:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME` (optional if token can resolve username)
- `TELEGRAM_WEBHOOK_SECRET`
- `TELEGRAM_SUBSCRIPTION_TOPICS`
- `TELEGRAM_SUBSCRIPTION_CORS_ORIGINS=https://topic-alerts.vercel.app`
- `KV_REST_API_URL`
- `KV_REST_API_TOKEN`
- `SUBSCRIPTION_STORAGE_PREFIX` (optional)

Then set Telegram webhook to:

`https://<your-vercel-domain>/api/telegram/webhook`
