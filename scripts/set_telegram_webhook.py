#!/usr/bin/env python3
"""Configure Telegram webhook for the subscription API service."""

import json
import os
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    webhook_url = os.environ.get("TELEGRAM_SUBSCRIPTION_WEBHOOK_URL", "").strip()
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()

    if len(sys.argv) > 1:
        token = sys.argv[1].strip()
    if len(sys.argv) > 2:
        webhook_url = sys.argv[2].strip()
    if len(sys.argv) > 3:
        secret = sys.argv[3].strip()

    if not token or not webhook_url:
        print("Usage: python scripts/set_telegram_webhook.py <BOT_TOKEN> <WEBHOOK_URL> [SECRET_TOKEN]")
        print("Or set TELEGRAM_BOT_TOKEN and TELEGRAM_SUBSCRIPTION_WEBHOOK_URL env vars.")
        return 1

    webhook_url = webhook_url.rstrip("/")
    if not webhook_url.endswith("/api/telegram/webhook"):
        webhook_url = f"{webhook_url}/api/telegram/webhook"

    payload = {
        "url": webhook_url,
        "allowed_updates": ["message"],
        "drop_pending_updates": False,
    }
    if secret:
        payload["secret_token"] = secret

    req = Request(
        f"https://api.telegram.org/bot{token}/setWebhook",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    print(json.dumps(body, indent=2))
    if not body.get("ok"):
        return 1

    info_req = Request(
        f"https://api.telegram.org/bot{token}/getWebhookInfo?{urlencode({})}",
        method="GET",
    )
    with urlopen(info_req, timeout=15) as resp:
        info = json.loads(resp.read().decode("utf-8"))

    print("\nWebhook info:")
    print(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
