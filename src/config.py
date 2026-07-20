from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class FilmWatch:
    id: str
    name: str


@dataclass
class PvrConfig:
    url: str
    city: str
    cid: str
    lat: str
    lng: str
    dates: List[str] = field(default_factory=list)


@dataclass
class Config:
    pvr: PvrConfig
    films: List[FilmWatch]
    poll_interval_seconds: int = 300
    state_file: str = "alerted_sessions.json"

    # Secret config (from .env)
    telegram_bot_token: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_to: str = ""

    # Better Stack logging (from .env)
    betterstack_source_token: str = ""
    betterstack_ingesting_host: str = "in.logtail.com"


def load_config(path: str = "config.yaml") -> Config:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    pvr_raw = raw["pvr"]
    pvr = PvrConfig(
        url=pvr_raw["url"],
        city=pvr_raw["city"],
        cid=pvr_raw["cid"],
        lat=pvr_raw.get("lat", ""),
        lng=pvr_raw.get("lng", ""),
        dates=pvr_raw.get("dates", []),
    )

    films = [FilmWatch(id=f["id"], name=f["name"]) for f in raw.get("films", [])]

    return Config(
        pvr=pvr,
        films=films,
        poll_interval_seconds=raw.get("poll_interval_seconds", 300),
        state_file=raw.get("state_file", "alerted_sessions.json"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        alert_email_to=os.getenv("ALERT_EMAIL_TO", ""),
        betterstack_source_token=os.getenv("BETTERSTACK_SOURCE_TOKEN", ""),
        betterstack_ingesting_host=os.getenv("BETTERSTACK_INGESTING_HOST", "in.logtail.com"),
    )
