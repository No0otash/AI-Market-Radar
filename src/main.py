import os
import json
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


CONFIG_FILE = "config.json"
STATE_FILE = "state.json"

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


with open(CONFIG_FILE, encoding="utf-8") as f:
    CONFIG = json.load(f)


def fetch(url):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AI-Market-Radar/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:

        return response.read()


def parse_rss(data):

    root = ET.fromstring(data)

    articles = []

    for item in root.findall(".//item"):

        title = (
            item.findtext("title")
            or ""
        ).strip()

        link = (
            item.findtext("link")
            or ""
        ).strip()

        description = (
            item.findtext("description")
            or ""
        ).strip()

        if title and link:

            articles.append({
                "title": title,
                "link": link,
                "description": description
            })

    return articles


def load_state():

    if not os.path.exists(STATE_FILE):

        return {
            "seen": []
        }

    try:

        with open(
            STATE_FILE,
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {
            "seen": []
        }


def save_state(state):

    state["seen"] = state["seen"][-1000:]

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2
        )


def article_id(article):

    raw = (
        article["title"]
        + article["link"]
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def analyze(article):

    text = (
        article["title"]
        + " "
        + article["description"]
    ).lower()

    impact = 0

    reasons = []


    # =========================
    # MACRO ECONOMIC
    # =========================

    macro_words = [

        "fed",
        "fomc",
        "ecb",
        "boj",

        "interest rate",
        "rate hike",
        "rate cut",

        "inflation",
        "cpi",
        "pce",

        "nfp",
        "nonfarm payroll",

        "unemployment",
        "gdp",
        "pmi"
    ]


    for word in macro_words:

        if word in text:

            impact += 1

            reasons.append(word)


    # =========================
    # GEOPOLITICAL RISK
    # =========================

    risk_words = [

        "war",
        "attack",
        "invasion",
        "sanctions",
        "crisis",
        "default",
        "bank failure",
        "conflict"
    ]


    for word in risk_words:

        if word in text:

            impact += 1.5

            reasons.append(word)


    # =========================
    # CRYPTO
    # =========================

    crypto_words = [

        "bitcoin",
        "ethereum",
        "crypto",
        "bitcoin etf",
        "crypto etf",
        "exchange hack",
        "crypto regulation"
    ]


    for word in crypto_words:

        if word in text:

            impact += 1.5

            reasons.append(word)


    # =========================
    # ENERGY
    # =========================

    energy_words = [

        "oil",
        "opec",
        "brent",
        "wti"
    ]


    for word in energy_words:

        if word in text:

            impact += 1

            reasons.append(word)


    impact = min(
        round(impact, 1),
        10
    )


    # =========================
    # MARKET DIRECTION
    # =========================

    direction = "NEUTRAL"


    bullish = [

        "rate cut",
        "dovish",
        "inflation falls",
        "cool cpi",
        "bitcoin etf approval",
        "crypto etf approval"
    ]


    bearish = [

        "rate hike",
        "hawkish",
        "inflation rises",
        "hot cpi",
        "bitcoin etf rejection",
        "exchange hack",
        "crypto ban"
    ]


    volatile = [

        "war",
        "attack",
        "invasion",
        "crisis",
        "bank failure"
    ]


    if any(
        x in text
        for x in volatile
    ):

        direction = "VOLATILE"

    elif any(
        x in text
        for x in bullish
    ):

        direction = "PUMP"

    elif any(
        x in text
        for x in bearish
    ):

        direction = "DUMP"


    # =========================
    # CONFIDENCE
    # =========================

    confidence = min(

        round(
            50 + impact * 4.5,
            1
        ),

        95
    )


    # =========================
    # AFFECTED MARKETS
    # =========================

    instruments = []


    if any(
        x in text
        for x in [

            "fed",
            "fomc",
            "cpi",
            "pce",
            "nfp",
            "inflation",
            "interest rate"
        ]
    ):

        instruments += [

            "EUR/USD",
            "GBP/USD",
            "USD/JPY",
            "XAU/USD",
            "DXY",
            "BTC/USDT",
            "NASDAQ"
        ]


    if any(
        x in text
        for x in [

            "bitcoin",
            "ethereum",
            "crypto",
            "exchange",
            "crypto etf"
        ]
    ):

        instruments += [

            "BTC/USDT",
            "ETH/USDT"
        ]


    if any(
        x in text
        for x in [

            "oil",
            "opec",
            "wti",
            "brent"
        ]
    ):

        instruments += [

            "WTI",
            "CAD"
        ]


    instruments = list(
        dict.fromkeys(instruments)
    )


    if not instruments:

        instruments = (
            CONFIG["watchlist"][:3]
        )


    # =========================
    # TIME HORIZON
    # =========================

    if impact >= 8:

        horizon = "15m - 4h"

    elif impact >= 6:

        horizon = "1h - 12h"

    else:

        horizon = "4h - 1D"


    return {

        "impact": impact,

        "direction": direction,

        "confidence": confidence,

        "instruments": instruments,

        "horizon": horizon,

        "reasons": reasons
    }


def send_telegram(message):

    url = (

        "https://api.telegram.org/"
        f"bot{TOKEN}/sendMessage"
    )


    data = urllib.parse.urlencode({

        "chat_id": CHAT_ID,

        "text": message,

        "disable_web_page_preview": "true"

    }).encode()


    request = urllib.request.Request(

        url,

        data=data,

        method="POST"
    )


    urllib.request.urlopen(

        request,

        timeout=20
    )


def main():

    state = load_state()

    alerts_sent = 0


    for feed in CONFIG["feeds"]:

        try:

            data = fetch(feed)

            articles = parse_rss(data)

        except Exception as error:

            print(
                "Feed error:",
                feed,
                error
            )

            continue


        for article in articles:

            uid = article_id(
                article
            )


            if uid in state["seen"]:

                continue


            state["seen"].append(uid)


            result = analyze(
                article
            )


            impact = result["impact"]


            if (
                impact
                < CONFIG[
                    "impact_threshold"
                ]
            ):

                continue


            if (
                alerts_sent
                >= CONFIG[
                    "max_alerts_per_run"
                ]
            ):

                break


            if (
                impact
                >= CONFIG[
                    "critical_threshold"
                ]
            ):

                level = (
                    "🚨 CRITICAL"
                )

            else:

                level = (
                    "⚡ HIGH IMPACT"
                )


            message = f"""
{level}

📰 {article["title"]}

📊 Market Impact:
{impact}/10

🎯 Direction:
{result["direction"]}

🧠 Confidence:
{result["confidence"]}%

⏱ Horizon:
{result["horizon"]}

💱 Affected Markets:
{", ".join(result["instruments"])}

🔎 Reason:
{", ".join(result["reasons"][:8])}

⚠️ Analytical signal,
not a guaranteed trade.

📰 Source:
{article["link"]}
""".strip()


            try:

                send_telegram(
                    message
                )

                alerts_sent += 1

                print(
                    "Alert sent:",
                    article["title"]
                )

            except Exception as error:

                print(
                    "Telegram error:",
                    error
                )


    save_state(state)


    print(
        f"Finished. "
        f"Alerts sent: {alerts_sent}"
    )


if __name__ == "__main__":

    main()
