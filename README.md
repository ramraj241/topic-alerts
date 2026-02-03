# AI Learning Agent for Medium

Automated pipeline that transforms Medium Data Engineering articles into beginner-friendly audio explanations, delivered daily via Telegram.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Medium RSS     │────▶│  AI Simplifier  │────▶│  Text-to-Speech │────▶│  Telegram Bot   │
│  (Data Eng)     │     │  (Claude/GPT)   │     │  (OpenAI TTS)   │     │  (Daily 7 AM)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
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
2. Go to Workflows → Import from File
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
├── docker-compose.yml      # n8n container setup
├── .env.example            # Environment template
├── config/
│   ├── feeds.json          # RSS feed sources
│   └── settings.json       # App configuration
├── n8n-workflows/
│   └── medium-to-audio-workflow.json
├── scripts/
│   ├── fetch_article.py    # Custom article parser
│   └── test_telegram.py    # Bot testing utility
├── templates/
│   └── explanation_prompt.txt
└── docs/
    └── setup-guide.md
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
