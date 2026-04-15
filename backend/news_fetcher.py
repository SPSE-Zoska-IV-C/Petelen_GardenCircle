import time
from datetime import datetime
from typing import List, Dict, Optional

import feedparser


_CACHE: Dict[str, object] = {"data": None, "ts": 0.0}


def _pick_best_image(items: list[dict]) -> Optional[str]:
    """Return highest-resolution candidate from feed metadata."""
    best_url: Optional[str] = None
    best_score = -1
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("href")
        if not url:
            continue
        width = item.get("width") or item.get("w") or 0
        height = item.get("height") or item.get("h") or 0
        try:
            width = int(width)
        except (TypeError, ValueError):
            width = 0
        try:
            height = int(height)
        except (TypeError, ValueError):
            height = 0
        score = width * height
        if score > best_score:
            best_score = score
            best_url = url
        elif best_score <= 0 and best_url is None:
            # Fallback for feeds that do not provide dimensions.
            best_url = url
    return best_url


def _extract_image(entry: dict) -> Optional[str]:
    # Prefer full-size media first to avoid pixelated thumbnails.
    media_content = entry.get("media_content") or []
    if isinstance(media_content, list):
        best = _pick_best_image(media_content)
        if best:
            return best

    enclosures = entry.get("enclosures") or []
    if isinstance(enclosures, list):
        best = _pick_best_image(enclosures)
        if best:
            return best

    thumbnails = entry.get("media_thumbnail") or []
    if isinstance(thumbnails, list):
        return _pick_best_image(thumbnails)
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


