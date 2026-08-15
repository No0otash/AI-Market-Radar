import os
import json
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


CONFIG_FILE = "config.json"
STATE_FILE = "state.json"

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# =========================================================
# VALIDATION
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is missing."
    )

if not CHAT_ID:
    raise RuntimeError(
        "TELEGRAM_CHAT_ID is missing."
    )

if not os.path.exists(CONFIG_FILE):
    raise RuntimeError(
        "config.json not found."
    )


with open(
    CONFIG_FILE,
    "r",
    encoding="utf-8"
) as f:

    CONFIG = json.load(f)


# =========================================================
# TELEGRAM
# =========================================================

def send_telegram(message):

    url = (
        "https://api.telegram.org/"
        f"bot{TOKEN.strip()}/sendMessage"
    )

    payload = urllib.parse.urlencode({

        "chat_id": CHAT_ID.strip(),

        "text": message,

        "disable_web_page_preview": "true"

    }).encode("utf-8")


    request = urllib.request.Request(

        url,

        data=payload,

        method="POST",

        headers={
            "Content-Type":
            "application/x-www-form-urlencoded"
        }
    )


    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        result = response.read().decode(
            "utf-8"
        )

        parsed = json.loads(result)

        if not parsed.get("ok"):

            raise RuntimeError(
                f"Telegram error: {result}"
            )

        return parsed


# =========================================================
# NEWS FETCH
# =========================================================

def fetch_feed(url):

    print(
        f"Fetching: {url}"
    )

    request = urllib.request.Request(

        url,

        headers={
            "User-Agent":
            "Mozilla/5.0 AI-Market-Radar/2.0"
        }
    )


    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        data = response.read()


    print(
        f"Downloaded: {len(data)} bytes"
    )

    return data


# =========================================================
# RSS / ATOM
# =========================================================

def parse_feed(data):

    root = ET.fromstring(data)

    articles = []


    # -------------------------
    # RSS
    # -------------------------

    for item in root.findall(
        ".//item"
    ):

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

                "description":
                description

            })


    # -------------------------
    # ATOM
    # -------------------------

    if not articles:

        namespace = {
            "atom":
            "http://www.w3.org/2005/Atom"
        }


        for entry in root.findall(
            ".//atom:entry",
            namespace
        ):

            title = (
                entry.findtext(
                    "atom:title",
                    default="",
                    namespaces=namespace
                )
                or ""
            ).strip()


            description = (
                entry.findtext(
                    "atom:summary",
                    default="",
                    namespaces=namespace
                )
                or ""
            ).strip()


            link = ""


            link_element = entry.find(
                "atom:link",
                namespace
            )


            if link_element is not None:

                link = (
                    link_element.attrib
                    .get("href", "")
                    .strip()
                )


            if title and link:

                articles.append({

                    "title": title,

                    "link": link,

                    "description":
                    description

                })


    return articles


# =========================================================
# STATE
# =========================================================

def load_state():

    if not os.path.exists(
        STATE_FILE
    ):

        return {
            "seen": []
        }


    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)


        if not isinstance(
            data,
            dict
        ):

            return {
                "seen": []
            }


        if "seen" not in data:

            data["seen"] = []


        return data


    except Exception:

        return {
            "seen": []
        }


def save_state(state):

    state["seen"] = (
        state["seen"][-2000:]
    )


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

        + "|"

        + article["link"]

    )


    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# =========================================================
# MARKET ANALYSIS
# =========================================================

def analyze(article):

    text = (

        article["title"]

        + " "

        + article["description"]

    ).lower()


    impact = 0.0

    reasons = []


    # =====================================================
    # CENTRAL BANKS
    # =====================================================

    central_bank = [

        "fed",
        "fomc",
        "ecb",
        "boj",
        "boe",
        "central bank"

    ]


    for word in central_bank:

        if word in text:

            impact += 2.0

            reasons.append(
                word
            )


    # =====================================================
    # RATES
    # =====================================================

    rates = [

        "interest rate",
        "rate hike",
        "rate cut",
        "rates higher",
        "rates lower"

    ]


    for word in rates:

        if word in text:

            impact += 2.0

            reasons.append(
                word
            )


    # =====================================================
    # MACRO DATA
    # =====================================================

    macro = [

        "inflation",
        "cpi",
        "pce",
        "nfp",
        "nonfarm payroll",
        "unemployment",
        "gdp",
        "pmi",
        "retail sales",
        "jobs report"

    ]


    for word in macro:

        if word in text:

            impact += 1.5

            reasons.append(
                word
            )


    # =====================================================
    # GEOPOLITICS
    # =====================================================

    geopolitical = [

        "war",
        "attack",
        "invasion",
        "missile",
        "sanctions",
        "conflict",
        "crisis",
        "ceasefire",
        "military",
        "iran",
        "israel",
        "russia",
        "ukraine",
        "china",
        "taiwan"

    ]


    for word in geopolitical:

        if word in text:

            impact += 1.5

            reasons.append(
                word
            )


    # =====================================================
    # CRYPTO
    # =====================================================

    crypto = [

        "bitcoin",
        "btc",
        "ethereum",
        "eth",
        "crypto",
        "bitcoin etf",
        "crypto etf",
        "exchange hack",
        "crypto regulation",
        "stablecoin"

    ]


    for word in crypto:

        if word in text:

            impact += 1.5

            reasons.append(
                word
            )


    # =====================================================
    # ENERGY
    # =====================================================

    energy = [

        "oil",
        "opec",
        "brent",
        "wti",
        "crude oil"

    ]


    for word in energy:

        if word in text:

            impact += 1.0

            reasons.append(
                word
            )


    impact = min(
        round(impact, 1),
        10.0
    )


    # =====================================================
    # DIRECTION
    # =====================================================

    direction = "NEUTRAL"


    pump_words = [

        "rate cut",
        "dovish",
        "inflation falls",
        "inflation cools",
        "cool cpi",
        "bitcoin etf approval",
        "crypto etf approval",
        "ceasefire"

    ]


    dump_words = [

        "rate hike",
        "hawkish",
        "inflation rises",
        "hot cpi",
        "bitcoin etf rejection",
        "crypto ban",
        "exchange hack"

    ]


    volatility_words = [

        "war",
        "attack",
        "invasion",
        "missile",
        "bank failure",
        "financial crisis",
        "military escalation"

    ]


    if any(
        x in text
        for x in volatility_words
    ):

        direction = "VOLATILE"


    elif any(
        x in text
        for x in pump_words
    ):

        direction = "PUMP"


    elif any(
        x in text
        for x in dump_words
    ):

        direction = "DUMP"


    # =====================================================
    # CONFIDENCE
    # =====================================================

    confidence = min(

        round(
            50 +
            impact * 4.5,
            1
        ),

        95.0

    )


    # =====================================================
    # AFFECTED MARKETS
    # =====================================================

    markets = []


    if any(
        x in text
        for x in [

            "fed",
            "fomc",
            "ecb",
            "boj",
            "boe",
            "cpi",
            "pce",
            "nfp",
            "inflation",
            "interest rate"

        ]
    ):

        markets += [

            "EUR/USD",
            "GBP/USD",
            "USD/JPY",
            "XAU/USD",
            "DXY",
            "BTC/USDT",
            "ETH/USDT",
            "NASDAQ"

        ]


    if any(
        x in text
        for x in crypto
    ):

        markets += [

            "BTC/USDT",
            "ETH/USDT"

        ]


    if any(
        x in text
        for x in energy
    ):

        markets += [

            "WTI",
            "CAD"

        ]


    if any(
        x in text
        for x in geopolitical
    ):

        markets += [

            "XAU/USD",
            "USD/JPY",
            "BTC/USDT"

        ]


    markets = list(
        dict.fromkeys(
            markets
        )
    )


    if not markets:

        markets = (
            CONFIG[
                "watchlist"
            ][:3]
        )


    # =====================================================
    # TIME HORIZON
    # =====================================================

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

        "markets": markets,

        "horizon": horizon,

        "reasons": list(
            dict.fromkeys(
                reasons
            )
        )

    }


# =========================================================
# FORMAT ALERT
# =========================================================

def format_alert(
    article,
    analysis
):

    impact = analysis[
        "impact"
    ]


    if impact >= 9:

        level = "🚨 CRITICAL"

    elif impact >= 7:

        level = "⚡ HIGH IMPACT"

    elif impact >= 4:

        level = "🟡 MARKET IMPACT"

    else:

        level = "📰 MARKET NEWS"


    reasons = analysis[
        "reasons"
    ]


    if reasons:

        signal_text = (
            ", ".join(
                reasons[:8]
            )
        )

    else:

        signal_text = (
            "General market news"
        )


    message = f"""
{level}

📰 {article["title"]}

━━━━━━━━━━━━━━━━

📊 IMPACT
{impact}/10

🎯 DIRECTION
{analysis["direction"]}

🧠 CONFIDENCE
{analysis["confidence"]}%

⏱ EXPECTED HORIZON
{analysis["horizon"]}

💱 AFFECTED MARKETS
{", ".join(analysis["markets"])}

🔎 SIGNALS
{signal_text}

━━━━━━━━━━━━━━━━

⚠️ News-based market signal.
Not guaranteed financial advice.

📰 SOURCE
{article["link"]}
""".strip()


    return message


# =========================================================
# MAIN
# =========================================================

def main():

    print("")
    print(
        "================================"
    )

    print(
        "      AI MARKET RADAR"
    )

    print(
        "================================"
    )


    state = load_state()


    total_articles = 0

    new_articles = 0

    alerts_sent = 0


    # =====================================================
    # FETCH ALL SOURCES
    # =====================================================

    for feed in CONFIG[
        "feeds"
    ]:

        try:

            data = fetch_feed(
                feed
            )

            articles = parse_feed(
                data
            )


            print(
                f"Articles found: "
                f"{len(articles)}"
            )


            total_articles += (
                len(articles)
            )


        except Exception as error:

            print(
                "FEED ERROR:",
                feed
            )

            print(
                error
            )

            continue


        # =================================================
        # PROCESS ARTICLES
        # =================================================

        for article in articles:

            uid = article_id(
                article
            )


            if uid in (
                state["seen"]
            ):

                continue


            new_articles += 1


            analysis = analyze(
                article
            )


            impact = analysis[
                "impact"
            ]


            threshold = float(
                CONFIG.get(
                    "impact_threshold",
                    0
                )
            )


            print(
                f"NEWS: "
                f"{article['title'][:80]}"
            )


            print(
                f"IMPACT: {impact}"
            )


            # ---------------------------------------------
            # SEND ALERT
            # ---------------------------------------------

            if impact >= threshold:

                if alerts_sent < int(
                    CONFIG.get(
                        "max_alerts_per_run",
                        5
                    )
                ):

                    message = (
                        format_alert(
                            article,
                            analysis
                        )
                    )


                    try:

                        send_telegram(
                            message
                        )


                        alerts_sent += 1


                        print(
                            "ALERT SENT"
                        )


                        # Only mark as seen
                        # AFTER successful send.

                        state[
                            "seen"
                        ].append(uid)


                    except Exception as error:

                        print(
                            "TELEGRAM ERROR:"
                        )

                        print(
                            error
                        )


                else:

                    print(
                        "ALERT LIMIT REACHED"
                    )

            else:

                # Low-impact news is still
                # marked as seen.

                state[
                    "seen"
                ].append(uid)


    save_state(
        state
    )


    print("")
    print(
        "================================"
    )

    print(
        f"TOTAL ARTICLES: "
        f"{total_articles}"
    )

    print(
        f"NEW ARTICLES: "
        f"{new_articles}"
    )

    print(
        f"ALERTS SENT: "
        f"{alerts_sent}"
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    main()
