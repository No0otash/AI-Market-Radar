import os
import json
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


# =========================================================
# CONFIGURATION
# =========================================================

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# =========================================================
# BASIC VALIDATION
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN secret is missing."
    )

if not CHAT_ID:
    raise RuntimeError(
        "TELEGRAM_CHAT_ID secret is missing."
    )


if not os.path.exists(CONFIG_FILE):
    raise RuntimeError(
        "config.json was not found."
    )


with open(
    CONFIG_FILE,
    "r",
    encoding="utf-8"
) as file:

    CONFIG = json.load(file)


# =========================================================
# TELEGRAM
# =========================================================

def send_telegram(message):

    print("Sending Telegram message...")

    url = (
        "https://api.telegram.org/"
        f"bot{TOKEN}/sendMessage"
    )

    payload = urllib.parse.urlencode({

        "chat_id": CHAT_ID,

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

        print(
            "Telegram response:",
            result
        )

        return result


# =========================================================
# NEWS DOWNLOAD
# =========================================================

def fetch_feed(url):

    print("")
    print("Fetching:")
    print(url)

    request = urllib.request.Request(

        url,

        headers={
            "User-Agent":
            "Mozilla/5.0 AI-Market-Radar/1.0"
        }
    )


    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        data = response.read()


    print(
        "Downloaded:",
        len(data),
        "bytes"
    )

    return data


# =========================================================
# RSS / ATOM PARSER
# =========================================================

def parse_feed(data):

    root = ET.fromstring(data)

    articles = []


    # -----------------------------------------------------
    # RSS
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # ATOM
    # -----------------------------------------------------

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
                    .get(
                        "href",
                        ""
                    )
                    .strip()
                )


            if title and link:

                articles.append({

                    "title": title,

                    "link": link,

                    "description":
                    description

                })


    print(
        "Articles found:",
        len(articles)
    )

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
        ) as file:

            return json.load(file)


    except Exception:

        return {
            "seen": []
        }


def save_state(state):

    state["seen"] = (
        state["seen"][-1000:]
    )


    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2
        )


def get_article_id(article):

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


    # -----------------------------------------------------
    # CENTRAL BANKS
    # -----------------------------------------------------

    central_bank_words = [

        "fed",
        "fomc",
        "ecb",
        "boj",
        "boe",
        "central bank"

    ]


    for word in central_bank_words:

        if word in text:

            impact += 1.5

            reasons.append(word)


    # -----------------------------------------------------
    # INTEREST RATES
    # -----------------------------------------------------

    rate_words = [

        "interest rate",
        "rate hike",
        "rate cut",
        "rates higher",
        "rates lower"

    ]


    for word in rate_words:

        if word in text:

            impact += 1.5

            reasons.append(word)


    # -----------------------------------------------------
    # INFLATION / ECONOMIC DATA
    # -----------------------------------------------------

    macro_words = [

        "inflation",
        "cpi",
        "pce",
        "nfp",
        "nonfarm payroll",
        "unemployment",
        "gdp",
        "pmi",
        "retail sales"

    ]


    for word in macro_words:

        if word in text:

            impact += 1.0

            reasons.append(word)


    # -----------------------------------------------------
    # GEOPOLITICS
    # -----------------------------------------------------

    geopolitical_words = [

        "war",
        "attack",
        "invasion",
        "missile",
        "sanctions",
        "conflict",
        "crisis",
        "ceasefire",
        "military"

    ]


    for word in geopolitical_words:

        if word in text:

            impact += 1.5

            reasons.append(word)


    # -----------------------------------------------------
    # CRYPTO
    # -----------------------------------------------------

    crypto_words = [

        "bitcoin",
        "ethereum",
        "crypto",
        "bitcoin etf",
        "crypto etf",
        "exchange hack",
        "crypto regulation",
        "stablecoin"

    ]


    for word in crypto_words:

        if word in text:

            impact += 1.5

            reasons.append(word)


    # -----------------------------------------------------
    # ENERGY
    # -----------------------------------------------------

    energy_words = [

        "oil",
        "opec",
        "brent",
        "wti"

    ]


    for word in energy_words:

        if word in text:

            impact += 1.0

            reasons.append(word)


    impact = min(
        round(impact, 1),
        10.0
    )


    # =====================================================
    # DIRECTION
    # =====================================================

    direction = "NEUTRAL"


    bullish_words = [

        "rate cut",
        "dovish",
        "inflation falls",
        "inflation cools",
        "cool cpi",
        "bitcoin etf approval",
        "crypto etf approval",
        "ceasefire"

    ]


    bearish_words = [

        "rate hike",
        "hawkish",
        "inflation rises",
        "hot cpi",
        "bitcoin etf rejection",
        "crypto ban",
        "exchange hack"

    ]


    volatile_words = [

        "war",
        "attack",
        "invasion",
        "missile",
        "bank failure",
        "financial crisis"

    ]


    if any(
        word in text
        for word in volatile_words
    ):

        direction = "VOLATILE"


    elif any(
        word in text
        for word in bullish_words
    ):

        direction = "PUMP"


    elif any(
        word in text
        for word in bearish_words
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

    instruments = []


    if any(
        word in text
        for word in [

            "fed",
            "fomc",
            "ecb",
            "boj",
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
            "ETH/USDT",
            "NASDAQ"

        ]


    if any(
        word in text
        for word in [

            "bitcoin",
            "ethereum",
            "crypto",
            "crypto etf",
            "exchange hack"

        ]
    ):

        instruments += [

            "BTC/USDT",
            "ETH/USDT"

        ]


    if any(
        word in text
        for word in [

            "oil",
            "opec",
            "brent",
            "wti"

        ]
    ):

        instruments += [

            "WTI",
            "CAD"

        ]


    if any(
        word in text
        for word in geopolitical_words
    ):

        instruments += [

            "XAU/USD",
            "USD/JPY",
            "BTC/USDT"

        ]


    instruments = list(
        dict.fromkeys(
            instruments
        )
    )


    if not instruments:

        instruments = (
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

        "instruments":
        instruments,

        "horizon":
        horizon,

        "reasons":
        reasons

    }


# =========================================================
# MAIN
# =========================================================

def main():

    print("")
    print(
        "================================"
    )
    print(
        "     AI MARKET RADAR STARTED"
    )
    print(
        "================================"
    )


    # -----------------------------------------------------
    # TELEGRAM TEST
    # -----------------------------------------------------

    test_message = (

        "🟢 AI MARKET RADAR\n\n"

        "Telegram connection test "
        "successful.\n\n"

        "Bot: @notash_news_bot"

    )


    try:

        send_telegram(
            test_message
        )

        print(
            "Telegram test: SUCCESS"
        )


    except Exception as error:

        print(
            "Telegram test: FAILED"
        )

        print(
            error
        )

        raise


    # -----------------------------------------------------
    # LOAD STATE
    # -----------------------------------------------------

    state = load_state()


    total_articles = 0

    alerts_sent = 0


    # -----------------------------------------------------
    # NEWS
    # -----------------------------------------------------

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


            total_articles += (
                len(articles)
            )


        except Exception as error:

            print(
                "FEED ERROR:"
            )

            print(
                feed
            )

            print(
                error
            )

            continue


        for article in articles:

            article_id = (
                get_article_id(
                    article
                )
            )


            if article_id in (
                state["seen"]
            ):

                continue


            state["seen"].append(
                article_id
            )


            analysis = analyze(
                article
            )


            impact = analysis[
                "impact"
            ]


            threshold = CONFIG[
                "impact_threshold"
            ]


            if impact < threshold:

                continue


            if alerts_sent >= (
                CONFIG[
                    "max_alerts_per_run"
                ]
            ):

                break


            if impact >= (
                CONFIG[
                    "critical_threshold"
                ]
            ):

                level = (
                    "🚨 CRITICAL"
                )


            elif impact >= 7:

                level = (
                    "⚡ HIGH IMPACT"
                )


            else:

                level = (
                    "📰 MARKET NEWS"
                )


            reasons = (
                ", ".join(
                    analysis[
                        "reasons"
                    ][:8]
                )
            )


            if not reasons:

                reasons = (
                    "General market news"
                )


            message = f"""

{level}

📰 {article["title"]}

📊 Market Impact:
{impact}/10

🎯 Direction:
{analysis["direction"]}

🧠 Confidence:
{analysis["confidence"]}%

⏱ Horizon:
{analysis["horizon"]}

💱 Affected Markets:
{", ".join(analysis["instruments"])}

🔎 Signals:
{reasons}

⚠️ Analytical signal,
not guaranteed financial advice.

📰 Source:
{article["link"]}

""".strip()


            try:

                send_telegram(
                    message
                )


                alerts_sent += 1


                print(
                    "ALERT SENT:"
                )

                print(
                    article["title"]
                )


            except Exception as error:

                print(
                    "TELEGRAM ERROR:"
                )

                print(
                    error
                )


    # -----------------------------------------------------
    # SAVE STATE
    # -----------------------------------------------------

    save_state(
        state
    )


    print("")
    print(
        "================================"
    )

    print(
        "TOTAL ARTICLES:",
        total_articles
    )

    print(
        "ALERTS SENT:",
        alerts_sent
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    main()
