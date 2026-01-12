import time
from datetime import datetime
from typing import List, Dict, Optional

import feedparser


_CACHE: Dict[str, object] = {"data": None, "ts": 0.0}


def _extract_image(entry: dict) -> Optional[str]:
    # Try media_thumbnail
    thumbnails = entry.get("media_thumbnail") or entry.get("media_thumbnail", [])
    if isinstance(thumbnails, list) and thumbnails:
        url = thumbnails[0].get("url")
        if url:
            return url
    # Try media_content/enclosures
    media_content = entry.get("media_content") or []
    if isinstance(media_content, list):
        for m in media_content:
            url = m.get("url")
            if url:
                return url
    enclosures = entry.get("enclosures") or []
    if isinstance(enclosures, list):
        for e in enclosures:
            url = e.get("href") or e.get("url")
            if url:
                return url
    return None


def _format_date(entry: dict) -> Optional[str]:
    # Prefer published, fallback to updated
    for key in ("published_parsed", "updated_parsed"):
        tm = entry.get(key)
        if tm:
            try:
                dt = datetime(*tm[:6])
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
    return None


def fetch_guardian_environment(limit: int = 12, bypass_cache: bool = False) -> List[Dict[str, str]]:
    global _CACHE
    ttl_seconds = 900  # 15 minutes
    now = time.time()
    if (not bypass_cache) and _CACHE["data"] and (now - float(_CACHE["ts"])) < ttl_seconds:
        return _CACHE["data"]  # type: ignore

    feed_url = "https://www.theguardian.com/environment/rss"
    parsed = feedparser.parse(feed_url)
    items: List[Dict[str, str]] = []

    for entry in parsed.entries or []:
        title = entry.get("title") or ""
        link = entry.get("link") or ""
        summary = (entry.get("summary") or "").strip()
        image = _extract_image(entry) or None
        published_at = _format_date(entry)

        items.append({
            "title": title,
            "summary": summary,
            "link": link,
            "image": image,
            "source": "The Guardian",
            "published_at": published_at,
        })

    # Limit after normalization
    items = items[:limit]

    _CACHE["data"] = items
    _CACHE["ts"] = now
    return items


