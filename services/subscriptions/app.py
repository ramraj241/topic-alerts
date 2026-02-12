"""Telegram topic subscription API.

Implements an end-to-end flow:
1) Web page posts selected topic to /api/telegram/subscribe
2) API returns Telegram deep link with one-time token
3) User opens bot and sends /start subscribe_<token>
4) Telegram webhook calls /api/telegram/webhook
5) API stores chat/topic subscription and confirms to the user
"""

from __future__ import annotations

import json
import os
import re
import secrets
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, Header, HTTPException, Request as FastAPIRequest
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="Telegram Topic Subscription API", version="1.0.0")

TOPIC_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,49}$")
START_PREFIX = "subscribe_"

DATA_DIR = Path(os.getenv("SUBSCRIPTION_DATA_DIR", "/app/data/subscriptions"))
PENDING_FILE = DATA_DIR / "pending_subscriptions.json"
SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"
LINK_STATUS_FILE = DATA_DIR / "subscription_link_status.json"

LINK_TTL_SECONDS = int(os.getenv("SUBSCRIPTION_LINK_TTL_SECONDS", "900"))
LINK_STATUS_RETENTION_SECONDS = int(os.getenv("SUBSCRIPTION_LINK_STATUS_RETENTION_SECONDS", "86400"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").strip().lstrip("@").lower()
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
DEFAULT_TOPICS = sorted(
    {
        topic.strip().lower()
        for topic in os.getenv(
            "TELEGRAM_SUBSCRIPTION_TOPICS",
            "data-engineering,machine-learning,cloud-architecture,ai-tools",
        ).split(",")
        if TOPIC_PATTERN.match(topic.strip().lower())
    }
)
_BOT_USERNAME_CACHE: str | None = BOT_USERNAME or None

_cors_origins_raw = os.getenv("TELEGRAM_SUBSCRIPTION_CORS_ORIGINS", "*").strip()
if _cors_origins_raw == "*":
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]

if not CORS_ORIGINS:
    CORS_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SubscribeRequest(BaseModel):
    topic: str


class TopicBroadcastRequest(BaseModel):
    text: str | None = None
    audio_url: str | None = None
    caption: str | None = None
    disable_web_page_preview: bool = True


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json_atomic(path: Path, payload: Any) -> None:
    _ensure_data_dir()
    with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=DATA_DIR) as tmp:
        json.dump(payload, tmp, ensure_ascii=True, indent=2, sort_keys=True)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _sanitize_topic(topic: str) -> str:
    clean = topic.strip().lower()
    if not TOPIC_PATTERN.match(clean):
        raise HTTPException(status_code=400, detail="Invalid topic format")
    return clean


def _prune_pending(pending: dict[str, dict[str, Any]], now: int) -> dict[str, dict[str, Any]]:
    return {
        token: record
        for token, record in pending.items()
        if isinstance(record, dict) and int(record.get("expires_at", 0)) > now
    }


def _prune_link_status(statuses: dict[str, dict[str, Any]], now: int) -> dict[str, dict[str, Any]]:
    pruned: dict[str, dict[str, Any]] = {}
    for token, record in statuses.items():
        if not isinstance(record, dict):
            continue
        expires_at = int(record.get("expires_at", 0))
        status = str(record.get("status", "")).strip().lower()
        confirmed_at = int(record.get("confirmed_at", 0))

        if status == "pending" and (expires_at + LINK_STATUS_RETENTION_SECONDS) > now:
            pruned[token] = record
            continue
        if status == "confirmed" and (confirmed_at + LINK_STATUS_RETENTION_SECONDS) > now:
            pruned[token] = record
    return pruned


def _telegram_api(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Telegram API HTTP error: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Telegram API network error: {exc.reason}") from exc

    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")
    return result


def _send_message(chat_id: int, text: str) -> None:
    _telegram_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
    )


def _send_audio(chat_id: int, audio_url: str, caption: str | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "audio": audio_url}
    if caption:
        payload["caption"] = caption
    _telegram_api("sendAudio", payload)


def _resolved_bot_username() -> str:
    global _BOT_USERNAME_CACHE
    if _BOT_USERNAME_CACHE:
        return _BOT_USERNAME_CACHE

    try:
        result = _telegram_api("getMe", {})
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Telegram bot username unavailable; configure TELEGRAM_BOT_USERNAME or verify TELEGRAM_BOT_TOKEN",
        ) from exc

    username = str((result.get("result") or {}).get("username") or "").strip().lstrip("@").lower()
    if not username:
        raise HTTPException(
            status_code=503,
            detail="Telegram bot username unavailable; configure TELEGRAM_BOT_USERNAME",
        )

    _BOT_USERNAME_CACHE = username
    return username


def _chat_topics(subs: dict[str, Any], chat_id: int) -> set[str]:
    chats = subs.get("chats", {})
    chat_data = chats.get(str(chat_id), {})
    return {str(topic).strip().lower() for topic in chat_data.get("topics", []) if str(topic).strip()}


def _save_chat_topics(subs: dict[str, Any], chat_id: int, topics_for_chat: set[str], now: int) -> None:
    chats = subs.setdefault("chats", {})
    topics = subs.setdefault("topics", {})
    chat_key = str(chat_id)

    existing = chats.get(chat_key, {})
    chats[chat_key] = {
        "chat_id": chat_id,
        "username": existing.get("username"),
        "first_name": existing.get("first_name"),
        "last_name": existing.get("last_name"),
        "topics": sorted(topics_for_chat),
        "updated_at": now,
    }

    for topic, chat_ids in list(topics.items()):
        filtered_ids = {str(cid) for cid in chat_ids if str(cid) != chat_key}
        if filtered_ids:
            topics[topic] = sorted(filtered_ids)
        else:
            del topics[topic]

    for topic in topics_for_chat:
        topic_chat_ids = set(topics.get(topic, []))
        topic_chat_ids.add(chat_key)
        topics[topic] = sorted(topic_chat_ids)


@app.on_event("startup")
def startup() -> None:
    _ensure_data_dir()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "telegram-subscriptions",
        "bot_username_configured": bool(BOT_USERNAME),
        "bot_token_configured": bool(BOT_TOKEN),
        "topics_count": len(DEFAULT_TOPICS),
    }


@app.get("/api/telegram/topics")
def get_topics() -> dict[str, Any]:
    return {"topics": DEFAULT_TOPICS}


@app.post("/api/telegram/subscribe")
def create_subscription_link(body: SubscribeRequest) -> dict[str, Any]:
    topic = _sanitize_topic(body.topic)
    bot_username = _resolved_bot_username()

    now = int(time.time())
    token = secrets.token_urlsafe(16)
    start_param = f"{START_PREFIX}{token}"

    pending = _read_json(PENDING_FILE, default={})
    pending = _prune_pending(pending, now)
    pending[token] = {
        "topic": topic,
        "created_at": now,
        "expires_at": now + LINK_TTL_SECONDS,
    }
    _write_json_atomic(PENDING_FILE, pending)
    statuses = _read_json(LINK_STATUS_FILE, default={})
    statuses = _prune_link_status(statuses, now)
    statuses[token] = {
        "topic": topic,
        "created_at": now,
        "expires_at": now + LINK_TTL_SECONDS,
        "status": "pending",
    }
    _write_json_atomic(LINK_STATUS_FILE, statuses)

    return {
        "ok": True,
        "topic": topic,
        "bot_username": bot_username,
        "start_param": start_param,
        "status_url": f"/api/telegram/subscribe/{start_param}/status",
        "deep_link": f"https://t.me/{bot_username}?start={start_param}",
        "expires_in_seconds": LINK_TTL_SECONDS,
    }


@app.get("/api/telegram/subscribe/{start_param}/status")
def get_subscription_link_status(start_param: str) -> dict[str, Any]:
    if not start_param.startswith(START_PREFIX):
        raise HTTPException(status_code=400, detail="Invalid start parameter")

    token = start_param[len(START_PREFIX):].strip()
    if not token:
        raise HTTPException(status_code=400, detail="Invalid start parameter")

    now = int(time.time())
    statuses = _read_json(LINK_STATUS_FILE, default={})
    statuses = _prune_link_status(statuses, now)
    _write_json_atomic(LINK_STATUS_FILE, statuses)
    record = statuses.get(token)
    if not isinstance(record, dict):
        return {"ok": True, "status": "invalid"}

    expires_at = int(record.get("expires_at", 0))
    status = str(record.get("status", "invalid")).strip().lower()
    topic = str(record.get("topic", "")).strip().lower()
    if status == "pending" and expires_at <= now:
        status = "expired"
    payload: dict[str, Any] = {
        "ok": True,
        "status": status,
        "topic": topic,
        "expires_at": expires_at,
        "expires_in_seconds": max(0, expires_at - now),
    }
    if status == "confirmed":
        payload["confirmed_at"] = int(record.get("confirmed_at", now))
    return payload


@app.post("/api/telegram/webhook")
async def telegram_webhook(
    request: FastAPIRequest,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    update = await request.json()
    message = update.get("message") or update.get("edited_message") or {}
    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return {"ok": True}

    if not text.startswith("/start") or " " not in text:
        if text == "/start":
            _send_message(
                chat_id,
                "Welcome. To subscribe, open the topic page and tap Subscribe on Telegram.\n"
                "Commands: /topics, /unsubscribe <topic>, /unsubscribe_all",
            )
        elif text == "/topics":
            subs = _read_json(SUBSCRIPTIONS_FILE, default={"chats": {}, "topics": {}})
            topics_for_chat = sorted(_chat_topics(subs, chat_id))
            if topics_for_chat:
                _send_message(chat_id, "You are subscribed to: " + ", ".join(topics_for_chat))
            else:
                _send_message(chat_id, "You are not subscribed to any topics yet.")
        elif text.startswith("/unsubscribe"):
            parts = text.split(maxsplit=1)
            if len(parts) == 1:
                _send_message(chat_id, "Usage: /unsubscribe <topic> or /unsubscribe_all")
            elif parts[1].strip().lower() == "all":
                now = int(time.time())
                subs = _read_json(SUBSCRIPTIONS_FILE, default={"chats": {}, "topics": {}})
                topics_for_chat = _chat_topics(subs, chat_id)
                if topics_for_chat:
                    _save_chat_topics(subs, chat_id, set(), now)
                    _write_json_atomic(SUBSCRIPTIONS_FILE, subs)
                    _send_message(chat_id, "Unsubscribed from all topics.")
                else:
                    _send_message(chat_id, "You are not subscribed to any topics.")
            else:
                try:
                    target_topic = _sanitize_topic(parts[1].strip())
                except HTTPException:
                    _send_message(chat_id, "Topic format is invalid. Use lowercase letters, numbers, and hyphens.")
                    return {"ok": True}
                now = int(time.time())
                subs = _read_json(SUBSCRIPTIONS_FILE, default={"chats": {}, "topics": {}})
                topics_for_chat = _chat_topics(subs, chat_id)
                if target_topic in topics_for_chat:
                    topics_for_chat.remove(target_topic)
                    _save_chat_topics(subs, chat_id, topics_for_chat, now)
                    _write_json_atomic(SUBSCRIPTIONS_FILE, subs)
                    _send_message(chat_id, f"Unsubscribed from: {target_topic}")
                else:
                    _send_message(chat_id, f"You are not subscribed to: {target_topic}")
        elif text == "/unsubscribe_all":
            now = int(time.time())
            subs = _read_json(SUBSCRIPTIONS_FILE, default={"chats": {}, "topics": {}})
            topics_for_chat = _chat_topics(subs, chat_id)
            if topics_for_chat:
                _save_chat_topics(subs, chat_id, set(), now)
                _write_json_atomic(SUBSCRIPTIONS_FILE, subs)
                _send_message(chat_id, "Unsubscribed from all topics.")
            else:
                _send_message(chat_id, "You are not subscribed to any topics.")
        return {"ok": True}

    payload = text.split(" ", 1)[1].strip()
    if not payload.startswith(START_PREFIX):
        return {"ok": True}

    token = payload[len(START_PREFIX):].strip()
    if not token:
        return {"ok": True}

    now = int(time.time())
    pending = _read_json(PENDING_FILE, default={})
    pending = _prune_pending(pending, now)
    record = pending.pop(token, None)
    _write_json_atomic(PENDING_FILE, pending)

    if not record:
        _send_message(chat_id, "This subscribe link is invalid or expired. Please generate a new one from the website.")
        return {"ok": True}

    topic = str(record.get("topic", "")).strip().lower()
    if not topic:
        _send_message(chat_id, "Could not process this subscription token. Please try again.")
        return {"ok": True}

    subs = _read_json(SUBSCRIPTIONS_FILE, default={"chats": {}, "topics": {}})
    chats = subs.setdefault("chats", {})
    current_topics = _chat_topics(subs, chat_id)
    current_topics.add(topic)
    chat_key = str(chat_id)

    from_user = message.get("from") or {}
    chats[chat_key] = {
        "chat_id": chat_id,
        "username": from_user.get("username"),
        "first_name": from_user.get("first_name"),
        "last_name": from_user.get("last_name"),
        "topics": sorted(current_topics),
        "updated_at": now,
    }

    topic_chat_ids = set(subs.setdefault("topics", {}).get(topic, []))
    topic_chat_ids.add(str(chat_id))
    subs["topics"][topic] = sorted(topic_chat_ids)

    _write_json_atomic(SUBSCRIPTIONS_FILE, subs)
    statuses = _read_json(LINK_STATUS_FILE, default={})
    statuses = _prune_link_status(statuses, now)
    statuses[token] = {
        "topic": topic,
        "created_at": int(record.get("created_at", now)),
        "expires_at": int(record.get("expires_at", now)),
        "status": "confirmed",
        "confirmed_at": now,
    }
    _write_json_atomic(LINK_STATUS_FILE, statuses)

    _send_message(chat_id, f"Subscribed successfully. You will now receive alerts for: {topic}")
    return {"ok": True}


@app.get("/api/telegram/topics/{topic}/chat-ids")
def get_chat_ids_for_topic(topic: str) -> dict[str, Any]:
    clean_topic = _sanitize_topic(topic)
    subs = _read_json(SUBSCRIPTIONS_FILE, default={"topics": {}})
    topic_chat_ids = subs.get("topics", {}).get(clean_topic, [])
    chat_ids = [int(chat_id) for chat_id in topic_chat_ids]
    return {"topic": clean_topic, "chat_ids": chat_ids}


@app.get("/api/telegram/subscriptions")
def get_subscriptions() -> dict[str, Any]:
    return _read_json(SUBSCRIPTIONS_FILE, default={"chats": {}, "topics": {}})


@app.post("/api/telegram/topics/{topic}/notify")
def notify_topic_subscribers(topic: str, body: TopicBroadcastRequest) -> dict[str, Any]:
    clean_topic = _sanitize_topic(topic)
    if not body.text and not body.audio_url:
        raise HTTPException(status_code=400, detail="At least one of text or audio_url is required")

    subs = _read_json(SUBSCRIPTIONS_FILE, default={"topics": {}})
    topic_chat_ids = subs.get("topics", {}).get(clean_topic, [])
    chat_ids = [int(chat_id) for chat_id in topic_chat_ids]

    delivered = 0
    failed: list[dict[str, Any]] = []

    for chat_id in chat_ids:
        try:
            if body.text:
                _telegram_api(
                    "sendMessage",
                    {
                        "chat_id": chat_id,
                        "text": body.text,
                        "disable_web_page_preview": body.disable_web_page_preview,
                    },
                )
            if body.audio_url:
                _send_audio(chat_id, body.audio_url, body.caption)
            delivered += 1
        except Exception as exc:  # pragma: no cover - network/API failure path
            failed.append({"chat_id": chat_id, "error": str(exc)})

    return {
        "topic": clean_topic,
        "subscriber_count": len(chat_ids),
        "delivered": delivered,
        "failed": failed,
    }
