#!/usr/bin/env python3
"""Additive OSINT risk monitor. Does not import or modify src/main.py.

The score is a transparent heuristic index, NOT a calibrated probability.
Only aggregate flight counts are retained; raw FR24 positions are not stored.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any

STATE_PATH = Path(os.getenv("RISK_STATE_PATH", "data/conflict_risk_state.json"))
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@HuntFlo").strip()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
FR24_API_TOKEN = os.getenv("FR24_API_TOKEN", "").strip()
ALERT_THRESHOLD = int(os.getenv("RISK_ALERT_THRESHOLD", "70"))
MIN_INDEPENDENT_DOMAINS = int(os.getenv("RISK_MIN_DOMAINS", "2"))
ALERT_COOLDOWN_HOURS = int(os.getenv("RISK_ALERT_COOLDOWN_HOURS", "24"))
FR24_BOUNDS = os.getenv("FR24_BOUNDS", "31,22,45,62")  # N,S,W,E; broad Gulf region
FR24_LIMIT = min(20, max(1, int(os.getenv("FR24_LIMIT", "20"))))

DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
]
FEEDS = [x.strip() for x in os.getenv("RISK_NEWS_FEEDS", ";".join(DEFAULT_FEEDS)).split(";") if x.strip()]
SHIP_API = "https://hormuz.data-tracking.net/api"

# Terms are intentionally broad; article text is only a signal for review, not proof.
REGION_TERMS = (
    "iran", "iranian", "persian gulf", "strait of hormuz", "gulf of oman",
    "israel", "united states", "u.s.", "american forces", "centcom",
    "middle east", "iraq", "qatar", "bahrain", "kuwait", "uae", "yemen",
)
ESCALATION_TERMS = (
    "airstrike", "air strike", "bombing", "missile attack", "drone attack",
    "military strike", "retaliation", "naval attack", "warship", "carrier strike",
    "evacuate", "evacuation", "embassy warning", "troops deployed",
    "ceasefire collapsed", "talks collapsed", "nuclear site", "hormuz closed",
    "ships attacked", "casualties", "mobilization",
)
DEESCALATION_TERMS = (
    "ceasefire agreement", "deal reached", "agreement reached", "talks resumed",
    "diplomatic breakthrough", "de-escalation", "deescalation", "truce extended",
)
HIGH_SEVERITY_TERMS = (
    "killed", "casualties", "airstrike", "missile attack", "bombing",
    "ships attacked", "ceasefire collapsed", "hormuz closed",
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fetch_bytes(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> bytes:
    request_headers = {"User-Agent": "AI-Market-Radar-ConflictMonitor/0.1", "Accept": "application/json, application/rss+xml, application/xml"}
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    return json.loads(fetch_bytes(url, headers).decode("utf-8", errors="replace"))


def load_state() -> dict[str, Any]:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("state is not an object")
        data.setdefault("daily", [])
        data.setdefault("last_alert_at", "")
        return data
    except (OSError, ValueError, json.JSONDecodeError):
        return {"daily": [], "last_alert_at": ""}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Retain only aggregates and 45 days of history; no raw aircraft or vessel positions.
    state["daily"] = state.get("daily", [])[-45:]
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_rss(url: str) -> list[dict[str, str]]:
    raw = fetch_bytes(url)
    root = ET.fromstring(raw)
    rows: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        title = " ".join((item.findtext("title") or "").split())
        description = " ".join((item.findtext("description") or "").split())
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if title:
            rows.append({"title": title, "description": description, "link": link, "pub_date": pub_date, "feed": url})
    # Atom fallback
    if not rows:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for item in root.findall(".//a:entry", ns):
            title = " ".join((item.findtext("a:title", default="", namespaces=ns)).split())
            summary = " ".join((item.findtext("a:summary", default="", namespaces=ns)).split())
            link_el = item.find("a:link", ns)
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            if title:
                rows.append({"title": title, "description": summary, "link": link, "pub_date": "", "feed": url})
    return rows


def host_of(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return url


def collect_news() -> dict[str, Any]:
    articles: list[dict[str, str]] = []
    errors: list[str] = []
    for feed in FEEDS:
        try:
            articles.extend(parse_rss(feed))
        except Exception as exc:
            errors.append(f"{host_of(feed)}: {type(exc).__name__}: {exc}")
    # Deduplicate across feeds by normalized title; syndicated copies do not count as independent.
    seen: set[str] = set()
    relevant: list[dict[str, str]] = []
    for article in articles:
        text = f"{article['title']} {article['description']}".lower()
        normalized = re.sub(r"[^a-z0-9]+", " ", article["title"].lower()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if any(term in text for term in REGION_TERMS) and any(term in text for term in ESCALATION_TERMS + DEESCALATION_TERMS):
            article["text"] = text
            article["domain"] = host_of(article["link"] or article["feed"])
            relevant.append(article)
    relevant.sort(key=lambda x: (sum(term in x["text"] for term in HIGH_SEVERITY_TERMS), x["pub_date"]), reverse=True)
    domains = sorted({a["domain"] for a in relevant if a["domain"]})
    high = [a for a in relevant if any(term in a["text"] for term in HIGH_SEVERITY_TERMS)]
    deescalation = [a for a in relevant if any(term in a["text"] for term in DEESCALATION_TERMS)]
    # A modest evidence score, capped; never a probability.
    score = min(45, len(domains) * 10 + min(5, len(high)) * 5)
    if deescalation and not high:
        score = max(0, score - 8)
    return {
        "score": score,
        "article_count": len(relevant),
        "high_severity_count": len(high),
        "deescalation_count": len(deescalation),
        "domains": domains,
        "headlines": [{"title": a["title"][:180], "link": a["link"], "domain": a["domain"]} for a in relevant[:6]],
        "errors": errors,
    }


def collect_shipping() -> dict[str, Any]:
    result: dict[str, Any] = {"available": False, "score": 0, "source": "hormuz.data-tracking.net", "error": ""}
    try:
        summary = fetch_json(f"{SHIP_API}/summary?hours=24")
        daily = fetch_json(f"{SHIP_API}/crossings/daily?days=14")
        crossings = summary.get("total_crossings")
        if crossings is None:
            crossings = summary.get("crossings")
        if isinstance(crossings, dict):
            crossings = crossings.get("total", crossings.get("count"))
        daily_rows = daily if isinstance(daily, list) else daily.get("data", daily.get("daily", [])) if isinstance(daily, dict) else []
        values: list[float] = []
        for row in daily_rows:
            if not isinstance(row, dict):
                continue
            value = row.get("total_crossings", row.get("crossings", row.get("count")))
            if isinstance(value, (int, float)):
                values.append(float(value))
        result.update({"available": True, "crossings_24h": crossings, "ships": summary.get("total_ships"), "last_poll": summary.get("last_poll"), "daily_crossings": values[-14:]})
        # Wait for at least 7 daily observations; traffic decline is a disruption indicator, not proof of military action.
        if isinstance(crossings, (int, float)) and len(values) >= 7:
            baseline = statistics.median(values[-8:-1] if len(values) >= 8 else values[:-1])
            result["baseline_crossings"] = baseline
            if baseline > 0:
                decline = (baseline - float(crossings)) / baseline
                result["decline_fraction"] = round(decline, 3)
                if decline >= 0.50:
                    result["score"] = 25
                elif decline >= 0.35:
                    result["score"] = 17
                elif decline >= 0.20:
                    result["score"] = 7
        return result
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def collect_flights(state: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"available": False, "score": 0, "source": "Flightradar24 API"}
    if not FR24_API_TOKEN:
        result["error"] = "FR24_API_TOKEN not configured; official API requires a separate subscription."
        return result
    url = "https://fr24api.flightradar24.com/api/live/flight-positions/light?" + urllib.parse.urlencode({"bounds": FR24_BOUNDS, "limit": FR24_LIMIT})
    headers = {
        "Authorization": f"Bearer {FR24_API_TOKEN}",
        "Accept": "application/json",
        "Accept-Version": "v1",
        "API Version": "v1",
    }
    try:
        payload = fetch_json(url, headers)
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        count = len(rows) if isinstance(rows, list) else 0
        # Store only the count, never raw positions/registration/callsign.
        history = [x.get("flight_count") for x in state.get("daily", []) if isinstance(x.get("flight_count"), int)]
        result.update({"available": True, "flight_count": count, "bounds": FR24_BOUNDS, "limit": FR24_LIMIT})
        if len(history) >= 7:
            baseline = statistics.median(history[-7:])
            result["baseline_count"] = baseline
            if baseline > 0:
                delta = abs(count - baseline) / baseline
                result["deviation_fraction"] = round(delta, 3)
                # A change in aggregate flight count is weak context only; never interpret it as intent.
                if delta >= 0.60:
                    result["score"] = 8
                elif delta >= 0.40:
                    result["score"] = 4
        return result
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def compose_assessment(news: dict[str, Any], shipping: dict[str, Any], flights: dict[str, Any]) -> dict[str, Any]:
    # This is a heuristic index (0-100), not a probability and not a substitute for analyst review.
    score = min(100, int(news.get("score", 0)) + int(shipping.get("score", 0)) + int(flights.get("score", 0)))
    elevated_domains: list[str] = []
    if news.get("high_severity_count", 0) >= 2 and len(news.get("domains", [])) >= MIN_INDEPENDENT_DOMAINS:
        elevated_domains.append("news")
    if shipping.get("score", 0) >= 17:
        elevated_domains.append("shipping")
    if flights.get("score", 0) >= 8:
        elevated_domains.append("aviation")
    return {"score": score, "elevated_domains": elevated_domains, "alert_eligible": score >= ALERT_THRESHOLD and len(elevated_domains) >= MIN_INDEPENDENT_DOMAINS}


def telegram_send(text: str) -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    if not CHANNEL_ID:
        raise RuntimeError("TELEGRAM_CHANNEL_ID is empty")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": CHANNEL_ID, "text": text, "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=25) as res:
        response = json.loads(res.read().decode("utf-8", errors="replace"))
    if not response.get("ok"):
        raise RuntimeError(f"Telegram rejected message: {response}")


def build_alert(news: dict[str, Any], shipping: dict[str, Any], flights: dict[str, Any], assessment: dict[str, Any]) -> str:
    lines = [
        "⚠️ هشدار پایش ریسک تشدید جنگ منطقه‌ای",
        "",
        f"شاخص ریسک تحلیلی: {assessment['score']}/100",
        "این امتیاز شاخص اولیه و غیرکالیبره است؛ به معنی احتمال وقوع " + str(assessment["score"]) + "٪ نیست.",
        "رویداد هدف: گسترش عمده جنگ منطقه‌ای با مشارکت آمریکا | افق پایش: ۳۰ روز",
        "",
        f"📰 اخبار: {news.get('article_count', 0)} مورد مرتبط؛ {news.get('high_severity_count', 0)} مورد با واژگان شدت بالا",
        f"🚢 کشتیرانی هرمز: امتیاز {shipping.get('score', 0)}/25" + (f"; تغییر عبور ۲۴ساعته: {shipping.get('decline_fraction')}" if shipping.get("decline_fraction") is not None else "; خط پایه کافی نیست"),
        f"✈️ پروازهای منطقه: امتیاز {flights.get('score', 0)}/8" + (f"; انحراف شمارش از خط پایه: {flights.get('deviation_fraction')}" if flights.get("deviation_fraction") is not None else "; خط پایه کافی نیست/منبع در دسترس نیست"),
        "",
        "این هشدار بر اساس چند خانواده داده عمومی است؛ جابه‌جایی هواپیما یا کاهش تردد کشتی به‌تنهایی نشانه قصد حمله نیست.",
        "منابع کشتیرانی: hormuz.data-tracking.net (CC BY 4.0؛ داده تقریبی AIS)",
    ]
    headlines = news.get("headlines", [])
    if headlines:
        lines.extend(["", "لینک‌های خبری برای بررسی:"])
        for item in headlines[:4]:
            if item.get("link"):
                lines.append(f"• {item['title']} — {item['link']}")
    return "\n".join(lines)


def main() -> int:
    state = load_state()
    print("Conflict Risk Monitor — daily run (heuristic only)")
    news = collect_news()
    shipping = collect_shipping()
    flights = collect_flights(state)
    assessment = compose_assessment(news, shipping, flights)
    today = now_utc().date().isoformat()
    row = {
        "date": today,
        "score": assessment["score"],
        "news_domains": news.get("domains", []),
        "high_severity_count": news.get("high_severity_count", 0),
        "ship_crossings_24h": shipping.get("crossings_24h") if isinstance(shipping.get("crossings_24h"), (int, float)) else None,
        "flight_count": flights.get("flight_count") if isinstance(flights.get("flight_count"), int) else None,
    }
    # One daily row only; retries on the same UTC date replace that date's observation.
    state["daily"] = [x for x in state.get("daily", []) if x.get("date") != today] + [row]
    state["daily"].sort(key=lambda x: x.get("date", ""))
    state["daily"] = state["daily"][-45:]
    print(json.dumps({"date": today, "assessment": assessment, "news": news, "shipping": shipping, "flights": flights}, ensure_ascii=False, indent=2))
    last_alert = state.get("last_alert_at", "")
    last_alert_score = int(state.get("last_alert_score", 0) or 0)
    alert_active = bool(state.get("alert_active", False))
    cooldown_ok = True
    if last_alert:
        try:
            last_dt = datetime.fromisoformat(last_alert.replace("Z", "+00:00"))
            cooldown_ok = (now_utc() - last_dt).total_seconds() >= ALERT_COOLDOWN_HOURS * 3600
        except ValueError:
            cooldown_ok = True
    should_alert = assessment["alert_eligible"] and cooldown_ok and (
        not alert_active or assessment["score"] >= last_alert_score + 10
    )
    if should_alert:
        try:
            telegram_send(build_alert(news, shipping, flights, assessment))
            state["last_alert_at"] = now_utc().isoformat()
            state["last_alert_score"] = assessment["score"]
            state["alert_active"] = True
            print("TELEGRAM_ALERT=sent")
        except Exception as exc:
            print(f"TELEGRAM_ALERT=failed: {type(exc).__name__}: {exc}", file=sys.stderr)
    else:
        if not assessment["alert_eligible"]:
            state["alert_active"] = False
        print(f"TELEGRAM_ALERT=not_sent (eligible={assessment['alert_eligible']}, cooldown_ok={cooldown_ok}, score={assessment['score']}, prior_alert_score={last_alert_score})")
    save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
