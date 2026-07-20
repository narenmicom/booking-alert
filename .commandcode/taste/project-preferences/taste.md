# Project Preferences
- Use Python for booking-alert type projects. Confidence: 0.50
- Use config.yaml for non-secret configuration (film IDs, dates, polling interval, city). Confidence: 0.70
- Auto-discover Telegram chat IDs via getUpdates instead of hardcoding. Confidence: 0.75
- Alert every poll cycle (no dedup) when matching shows are found. Confidence: 0.70
- Support multiple film IDs in config.yaml for multi-movie alerts. Confidence: 0.70
- Keep email alerts optional via .env configuration. Confidence: 0.65
- Add --test mode to verify connectivity to all services. Confidence: 0.70
- Include timestamp in alert messages. Confidence: 0.65
- Use Better Stack (logtail-python) for external log shipping. Confidence: 0.70
