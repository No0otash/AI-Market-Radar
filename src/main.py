import os
import json
import hashlib
import re
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


CONFIG_FILE = "config.json"
STATE_FILE = "state.json"

TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT_ID = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()


# =========================================================
# VALIDATION
# =========================================================

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing.")

if not CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID is missing.")

if not os.path.exists(CONFIG_FILE):
    raise RuntimeError("config.json not found.")


with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


# =========================================================
# PERSIAN FINANCIAL DICTIONARY
# =========================================================

FA = {
    "fed": "فدرال رزرو",
    "federal reserve": "فدرال رزرو",
    "ecb": "بانک مرکزی اروپا",
    "boj": "بانک مرکزی ژاپن",
    "boe": "بانک مرکزی انگلیس",
    "central bank": "بانک مرکزی",

    "interest rate": "نرخ بهره",
    "rate cut": "کاهش نرخ بهره",
    "rate hike": "افزایش نرخ بهره",
    "rates higher": "نرخ‌های بهره بالاتر",
    "rates lower": "نرخ‌های بهره پایین‌تر",

    "inflation": "تورم",
    "cpi": "شاخص قیمت مصرف‌کننده (CPI)",
    "pce": "شاخص PCE",
    "nfp": "اشتغال غیرکشاورزی (NFP)",
    "nonfarm payroll": "اشتغال غیرکشاورزی",
    "unemployment": "بیکاری",
    "gdp": "تولید ناخالص داخلی (GDP)",
    "pmi": "شاخص مدیران خرید (PMI)",
    "retail sales": "خرده‌فروشی",
    "jobs report": "گزارش اشتغال",

    "bitcoin": "بیت‌کوین",
    "btc": "بیت‌کوین (BTC)",
    "ethereum": "اتریوم",
    "eth": "اتریوم (ETH)",
    "crypto": "ارزهای دیجیتال",
    "cryptocurrency": "ارز دیجیتال",
    "bitcoin etf": "ETF بیت‌کوین",
    "crypto etf": "ETF کریپتو",
    "stablecoin": "استیبل‌کوین",
    "exchange hack": "هک صرافی",
    "crypto regulation": "مقررات ارزهای دیجیتال",

    "oil": "نفت",
    "crude oil": "نفت خام",
    "oil prices": "قیمت نفت",
    "opec": "اوپک",
    "brent": "برنت",
    "wti": "WTI",

    "gold": "طلا",
    "dollar": "دلار",
    "usd": "دلار آمریکا",
    "euro": "یورو",
    "japan": "ژاپن",
    "china": "چین",
    "taiwan": "تایوان",

    "iran": "ایران",
    "israel": "اسرائیل",
    "russia": "روسیه",
    "ukraine": "اوکراین",

    "war": "جنگ",
    "attack": "حمله",
    "invasion": "تهاجم",
    "missile": "موشک",
    "sanctions": "تحریم‌ها",
    "conflict": "درگیری",
    "crisis": "بحران",
    "ceasefire": "آتش‌بس",
    "military": "نظامی",
    "military escalation": "تشدید تنش نظامی",

    "higher": "افزایش",
    "lower": "کاهش",
    "rises": "افزایش یافت",
    "falls": "کاهش یافت",
    "surges": "جهش کرد",
    "plunges": "سقوط کرد",
    "unexpectedly": "به‌طور غیرمنتظره",

    "approval": "تأیید",
    "rejection": "رد",
    "hack": "هک",
    "regulation": "مقررات",

    "stocks": "سهام",
    "stock market": "بازار سهام",
    "market": "بازار",
    "markets": "بازارها",
    "bank": "بانک",
    "banks": "بانک‌ها",
}


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =========================================================
# FREE PERSIAN TRANSLATION
# =========================================================

def translate_text(text):

    text = clean_text(text)

    if not text:
        return ""

    if not CONFIG.get(
        "translation_enabled",
        True
    ):
        return text

    # Public translation endpoint.
    try:

        query = text[:450]

        url = (
            "https://api.mymemory.translated.net/get?"
            + urllib.parse.urlencode({
                "q": query,
                "langpair": "en|fa"
            })
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                "AI-Market-Radar/3.0"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=12
        ) as response:

            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        translated = clean_text(
            (
                data.get(
                    "responseData"
                ) or {}
            ).get(
                "translatedText",
                ""
            )
        )

        if translated:

            return translated

    except Exception as error:

        print(
            "Translation service unavailable:",
            error
        )


    # =====================================================
    # LOCAL FALLBACK
    # =====================================================

    result = text

    for english, persian in sorted(
        FA.items(),
        key=lambda item:
        len(item[0]),
        reverse=True
    ):

        result = re.sub(
            r"\b"
            + re.escape(english)
            + r"\b",
            persian,
            result,
            flags=re.IGNORECASE
        )

    return result


# =========================================================
# TELEGRAM
# =========================================================

def send_telegram(message):

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

        result = json.loads(
            response.read().decode(
                "utf-8"
            )
        )


    if not result.get("ok"):

        raise RuntimeError(
            f"Telegram error: {result}"
        )


    return result


# =========================================================
# RSS FETCH
# =========================================================

def fetch_feed(url):

    print(
        f"Fetching: {url}"
    )

    request = urllib.request.Request(

        url,

        headers={
            "User-Agent":
            "Mozilla/5.0 AI-Market-Radar/3.0"
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
# RSS / ATOM PARSER
# =========================================================

def parse_feed(data):

    root = ET.fromstring(data)

    articles = []


    # =====================================================
    # RSS
    # =====================================================

    for item in root.findall(
        ".//item"
    ):

        title = clean_text(
            item.findtext(
                "title"
            ) or ""
        )

        link = (
            item.findtext(
                "link"
            ) or ""
        ).strip()

        description = clean_text(
            item.findtext(
                "description"
            ) or ""
        )


        if title and link:

            articles.append({

                "title": title,

                "link": link,

                "description":
                description

            })


    # =====================================================
    # ATOM
    # =====================================================

    if not articles:

        namespace = {
            "atom":
            "http://www.w3.org/2005/Atom"
        }


        for entry in root.findall(
            ".//atom:entry",
            namespace
        ):

            title = clean_text(
                entry.findtext(
                    "atom:title",
                    default="",
                    namespaces=namespace
                )
            )


            description = clean_text(
                entry.findtext(
                    "atom:summary",
                    default="",
                    namespaces=namespace
                )
            )


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


        if not isinstance(
            data.get("seen"),
            list
        ):

            data["seen"] = []


        return data


    except Exception:

        return {
            "seen": []
        }


def save_state(state):

    state["seen"] = (
        state.get(
            "seen",
            []
        )[-2000:]
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


    # =====================================================
    # CENTRAL BANKS
    # =====================================================

    groups = [

        (
            [
                "fed",
                "fomc",
                "ecb",
                "boj",
                "boe",
                "central bank"
            ],
            2.0
        ),

        (
            [
                "interest rate",
                "rate hike",
                "rate cut",
                "rates higher",
                "rates lower"
            ],
            2.0
        ),

        (
            [
                "inflation",
                "cpi",
                "pce",
                "nfp",
                "nonfarm payroll",
                "unemployment",
                "gdp",
                "pmi",
                "jobs report"
            ],
            1.5
        ),

        (
            [
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
            ],
            1.5
        ),

        (
            [
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
            ],
            1.5
        ),

        (
            [
                "oil",
                "opec",
                "brent",
                "wti",
                "crude oil"
            ],
            1.0
        )

    ]


    for words, weight in groups:

        for word in words:

            if word in text:

                impact += weight

                reasons.append(
                    word
                )


    impact = min(
        round(
            impact,
            1
        ),
        10.0
    )


    # =====================================================
    # DIRECTION
    # =====================================================

    if any(
        word in text
        for word in [

            "war",
            "attack",
            "invasion",
            "missile",
            "bank failure",
            "financial crisis",
            "military escalation"

        ]
    ):

        direction = (
            "🟡 نوسانی / ریسک‌گریز"
        )


    elif any(
        word in text
        for word in [

            "rate cut",
            "dovish",
            "inflation falls",
            "inflation cools",
            "cool cpi",
            "bitcoin etf approval",
            "crypto etf approval",
            "ceasefire"

        ]
    ):

        direction = (
            "🟢 صعودی احتمالی"
        )


    elif any(
        word in text
        for word in [

            "rate hike",
            "hawkish",
            "inflation rises",
            "hot cpi",
            "bitcoin etf rejection",
            "crypto ban",
            "exchange hack"

        ]
    ):

        direction = (
            "🔴 نزولی احتمالی"
        )


    else:

        direction = (
            "⚪ خنثی / نامشخص"
        )


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
        word in text
        for word in [

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
        word in text
        for word in [

            "bitcoin",
            "btc",
            "ethereum",
            "eth",
            "crypto",
            "crypto etf",
            "exchange hack"

        ]
    ):

        markets += [

            "BTC/USDT",
            "ETH/USDT"

        ]


    if any(
        word in text
        for word in [

            "oil",
            "opec",
            "brent",
            "wti",
            "crude oil"

        ]
    ):

        markets += [

            "WTI",
            "CAD"

        ]


    if any(
        word in text
        for word in [

            "war",
            "attack",
            "invasion",
            "missile",
            "sanctions",
            "conflict",
            "crisis",
            "iran",
            "israel",
            "russia",
            "ukraine",
            "china",
            "taiwan"

        ]
    ):

        markets += [

            "XAU/USD",
            "USD/JPY",
            "BTC/USDT",
            "WTI"

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
    # ASSET DIRECTION
    # =====================================================

    asset_view = {}


    for market in markets:

        view = (
            "⚪ نامشخص"
        )


        if market in [
            "EUR/USD",
            "GBP/USD"
        ]:

            if any(
                x in text
                for x in [
                    "fed",
                    "fomc",
                    "rate hike",
                    "hawkish",
                    "hot cpi"
                ]
            ):

                view = "🔴 نزولی"


        if market == "USD/JPY":

            if any(
                x in text
                for x in [
                    "fed",
                    "rate hike",
                    "hawkish",
                    "hot cpi"
                ]
            ):

                view = "🟢 صعودی"


        if market == "XAU/USD":

            if any(
                x in text
                for x in [
                    "rate hike",
                    "hawkish",
                    "hot cpi"
                ]
            ):

                view = "🔴 نزولی"


        if market in [
            "BTC/USDT",
            "ETH/USDT"
        ]:

            if any(
                x in text
                for x in [
                    "bitcoin etf approval",
                    "crypto etf approval",
                    "rate cut",
                    "dovish"
                ]
            ):

                view = "🟢 صعودی"


            elif any(
                x in text
                for x in [
                    "exchange hack",
                    "crypto ban",
                    "rate hike",
                    "hawkish"
                ]
            ):

                view = "🔴 نزولی"


        if market == "WTI":

            if any(
                x in text
                for x in [
                    "war",
                    "attack",
                    "opec",
                    "supply disruption"
                ]
            ):

                view = "🟢 صعودی"


        asset_view[
            market
        ] = view


    # =====================================================
    # TIME HORIZON
    # =====================================================

    if impact >= 8:

        horizon = (
            "۱۵ دقیقه تا ۴ ساعت"
        )

    elif impact >= 6:

        horizon = (
            "۱ تا ۱۲ ساعت"
        )

    else:

        horizon = (
            "۴ ساعت تا ۱ روز"
        )


    return {

        "impact":
        impact,

        "direction":
        direction,

        "confidence":
        confidence,

        "markets":
        markets,

        "asset_view":
        asset_view,

        "horizon":
        horizon,

        "reasons":
        list(
            dict.fromkeys(
                reasons
            )
        )

    }


# =========================================================
# TELEGRAM MESSAGE
# =========================================================

def format_alert(
    article,
    analysis
):

    if analysis[
        "impact"
    ] >= 9:

        level = (
            "🚨 هشدار بحرانی بازار"
        )

    elif analysis[
        "impact"
    ] >= 7:

        level = (
            "⚡ هشدار پراثر بازار"
        )

    else:

        level = (
            "📰 خبر مؤثر بر بازار"
        )


    title_fa = translate_text(
        article["title"]
    )


    description_fa = translate_text(
        article[
            "description"
        ][:500]
    )


    if not description_fa:

        description_fa = (
            "توضیحات کافی برای خلاصه خبر در دسترس نیست."
        )


    views = "\n".join(

        f"{market}: {view}"

        for market, view

        in analysis[
            "asset_view"
        ].items()

    )


    if analysis[
        "reasons"
    ]:

        reason_fa = translate_text(

            ", ".join(
                analysis[
                    "reasons"
                ][:8]
            )

        )

    else:

        reason_fa = (
            "سیگنال مشخصی شناسایی نشد."
        )


    message = f"""
{level}

📰 {title_fa}

━━━━━━━━━━━━━━━━

📊 شدت اثر بازار:
{analysis["impact"]}/10

🎯 جهت احتمالی:
{analysis["direction"]}

🧠 اطمینان تحلیلی:
{analysis["confidence"]}٪

⏱ افق زمانی اثر:
{analysis["horizon"]}

━━━━━━━━━━━━━━━━

💱 اثر احتمالی روی بازارها:

{views}

━━━━━━━━━━━━━━━━

🔎 سیگنال‌های شناسایی‌شده:

{reason_fa}

━━━━━━━━━━━━━━━━

📝 خلاصه خبر:

{description_fa}

━━━━━━━━━━━━━━━━

⚠️ این پیام یک تحلیل خبری خودکار است.
جهت بازار قطعی نیست و تضمین سود یا توصیه قطعی معامله محسوب نمی‌شود.

📰 منبع:
{article["link"]}
""".strip()


    return message


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "================================"
    )

    print(
        "       AI MARKET RADAR"
    )

    print(
        "================================"
    )


    state = load_state()


    total_articles = 0

    new_articles = 0

    alerts_sent = 0


    threshold = float(
        CONFIG.get(
            "impact_threshold",
            6.0
        )
    )


    max_alerts = int(
        CONFIG.get(
            "max_alerts_per_run",
            5
        )
    )


    # =====================================================
    # FETCH NEWS
    # =====================================================

    for feed in CONFIG.get(
        "feeds",
        []
    ):

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


        except Exception as error:

            print(
                "FEED ERROR:",
                feed
            )

            print(
                error
            )

            continue


        total_articles += (
            len(articles)
        )


        # =================================================
        # PROCESS
        # =================================================

        for article in articles:

            uid = get_article_id(
                article
            )


            if uid in (
                state[
                    "seen"
                ]
            ):

                continue


            new_articles += 1


            analysis = analyze(
                article
            )


            impact = analysis[
                "impact"
            ]


            print(
                f"NEWS: "
                f"{article['title'][:100]}"
            )


            print(
                f"IMPACT: {impact}/10"
            )


            # =================================================
            # LOW IMPACT
            # =================================================

            if impact < threshold:

                state[
                    "seen"
                ].append(
                    uid
                )

                continue


            # =================================================
            # ALERT LIMIT
            # =================================================

            if alerts_sent >= max_alerts:

                continue


            # =================================================
            # SEND
            # =================================================

            message = format_alert(
                article,
                analysis
            )


            try:

                send_telegram(
                    message
                )


                alerts_sent += 1


                state[
                    "seen"
                ].append(
                    uid
                )


                print(
                    "ALERT SENT"
                )


            except Exception as error:

                print(
                    "TELEGRAM ERROR:",
                    error
                )


    # =====================================================
    # SAVE STATE
    # =====================================================

    save_state(
        state
    )


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
