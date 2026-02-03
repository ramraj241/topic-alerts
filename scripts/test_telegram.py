#!/usr/bin/env python3
"""
Test Telegram bot connection and send a test message.
Run this to verify your bot token and chat ID are correct.
"""

import os
import sys
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> dict:
    """Send a test message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    req = Request(url, data=data, headers=headers, method="POST")

    try:
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        return {"ok": False, "error": e.read().decode("utf-8")}
    except URLError as e:
        return {"ok": False, "error": str(e.reason)}


def get_bot_info(bot_token: str) -> dict:
    """Get bot information to verify token."""
    url = f"https://api.telegram.org/bot{bot_token}/getMe"

    try:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    # Get credentials from environment or arguments
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if len(sys.argv) >= 3:
        bot_token = sys.argv[1]
        chat_id = sys.argv[2]

    if not bot_token or not chat_id:
        print("Usage: python test_telegram.py <BOT_TOKEN> <CHAT_ID>")
        print("   or: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars")
        sys.exit(1)

    print("Testing Telegram Bot Connection...")
    print("-" * 40)

    # Test 1: Verify bot token
    print("\n1. Verifying bot token...")
    bot_info = get_bot_info(bot_token)

    if bot_info.get("ok"):
        bot = bot_info["result"]
        print(f"   Bot Name: {bot.get('first_name')}")
        print(f"   Username: @{bot.get('username')}")
    else:
        print(f"   ERROR: {bot_info.get('error')}")
        sys.exit(1)

    # Test 2: Send test message
    print("\n2. Sending test message...")
    test_message = """
*AI Learning Agent Test*

If you see this message, your Telegram bot is configured correctly.

Next steps:
1. Import the n8n workflow
2. Configure OpenAI credentials
3. Activate the workflow
"""

    result = send_telegram_message(bot_token, chat_id, test_message)

    if result.get("ok"):
        print("   Message sent successfully!")
        print(f"   Message ID: {result['result']['message_id']}")
    else:
        print(f"   ERROR: {result.get('error')}")
        print("\n   Common issues:")
        print("   - Wrong chat ID (message @userinfobot to get yours)")
        print("   - Bot not started (send /start to your bot first)")
        sys.exit(1)

    print("\n" + "-" * 40)
    print("All tests passed! Your Telegram bot is ready.")


if __name__ == "__main__":
    main()
