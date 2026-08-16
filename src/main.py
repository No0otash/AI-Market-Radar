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

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()


# =========================================================
# CONFIG
# =========================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing.")

if not CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID is missing.")

if not HF_TOKEN:
    print("WARNING: HF_TOKEN is missing. AI analysis will use fallback mode.")


with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


# =========================================================
# PERSIAN FALLBACK DICTIONARY
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
    "inflation": "تورم",
    "cpi": "شاخص قیمت مصرف‌کننده",
    "pce": "شاخص PCE",
    "nfp": "اشتغال غیرکشاورزی",
    "unemployment": "بیکاری",
    "gdp": "تولید ناخالص داخلی",
    "pmi": "شاخص مدیران خرید",

    "bitcoin": "بیت‌کوین",
    "btc": "بیت‌کوین",
    "ethereum": "اتریوم",
    "eth": "اتریوم",
    "crypto": "ارزهای دیجیتال",
    "cryptocurrency": "ارز دیجیتال",
    "bitcoin etf": "ETF بیت‌کوین",
    "crypto etf": "ETF کریپتو",
    "stablecoin": "استیبل‌کوین",

    "oil": "نفت",
    "crude oil": "نفت خام",
    "opec": "اوپک",
    "brent": "برنت",
    "wti": "WTI",

    "gold": "طلا",
    "dollar": "دلار",
    "euro": "یورو",
    "china": "چین",
    "japan": "ژاپن",
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

    "higher": "افزایش",
    "lower": "کاهش",
    "rises": "افزایش یافت",
    "falls": "کاهش یافت",
    "surges": "جهش کرد",
    "plunges": "سقوط کرد",

    "approval": "تأیید",
    "rejection": "رد",
    "hack": "هک",
    "regulation": "مقررات"
}


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(text):

    text = html.unescape(text or "")

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# FREE TRANSLATION
# =========================================================

def translate_text(text):

    text = clean_text(text)

    if not text:
        return ""

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
                "AI-Market-Radar/4.0"
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
            "Translation unavailable:",
            error
        )


    # Local fallback

    result = text

    for english, persian in sorted(
        FA.items(),
        key=lambda x: len(x[0]),
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
        f"bot{TELEGRAM_TOKEN}/sendMessage"
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
            result
        )


# =========================================================
# RSS
# =========================================================

def fetch_feed(url):

    request = urllib.request.Request(

        url,

        headers={
            "User-Agent":
            "Mozilla/5.0 AI-Market-Radar"
        }
    )


    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return response.read()


# =========================================================
# RSS PARSER
# =========================================================

def parse_feed(data):

    root = ET.fromstring(data)

    articles = []


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


    return articles


# =========================================================
# STATE
# =========================================================

def load_state():

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(
            data.get("seen"),
            list
        ):

            return data

    except Exception:
        pass


    return {
        "seen": []
    }


def save_state(state):

    state["seen"] = (
        state.get(
            "seen",
            []
        )[-3000:]
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
# INITIAL MARKET FILTER
# =========================================================

def calculate_impact(article):

    text = (
        article["title"]
        + " "
        + article["description"]
    ).lower()


    impact = 0

    keywords = {

        "fed": 2,
        "fomc": 2,
        "ecb": 2,
        "boj": 2,
        "boe": 2,

        "interest rate": 2,
        "rate hike": 2,
        "rate cut": 2,

        "inflation": 2,
        "cpi": 2,
        "pce": 2,
        "nfp": 2,
        "unemployment": 1.5,
        "gdp": 1.5,
        "pmi": 1.5,

        "bitcoin": 1.5,
        "btc": 1.5,
        "ethereum": 1.5,
        "crypto": 1.5,
        "bitcoin etf": 2,

        "war": 2,
        "attack": 2,
        "invasion": 2,
        "missile": 2,
        "sanctions": 1.5,
        "conflict": 1.5,
        "crisis": 1.5,

        "oil": 1,
        "opec": 1.5,
        "brent": 1,
        "wti": 1,

        "china": 1,
        "taiwan": 1.5,
        "iran": 1.5,
        "israel": 1.5,
        "russia": 1.5,
        "ukraine": 1.5
    }


    for word, weight in keywords.items():

        if word in text:
            impact += weight


    return min(
        round(impact, 1),
        10
    )


# =========================================================
# AI ANALYST
# =========================================================

def ai_analyze(article):

    if not HF_TOKEN:

        return fallback_analysis(
            article
        )


    title = article[
        "title"
    ]

    description = article[
        "description"
    ]


    prompt = f"""
You are a professional macro and financial market analyst.

Analyze this news for Forex, Crypto, Gold, Oil and stock indices.

NEWS TITLE:
{title}

NEWS DESCRIPTION:
{description}

Return ONLY valid JSON.

Use this exact structure:

{{
  "persian_title": "",
  "summary_fa": "",
  "impact": 0,
  "direction": "",
  "confidence": 0,
  "time_horizon": "",
  "forex": {{
    "EUR/USD": "",
    "GBP/USD": "",
    "USD/JPY": "",
    "DXY": ""
  }},
  "crypto": {{
    "BTC/USDT": "",
    "ETH/USDT": ""
  }},
  "commodities": {{
    "XAU/USD": "",
    "WTI": ""
  }},
  "indices": {{
    "NASDAQ": "",
    "SP500": ""
  }},
  "reason_fa": ""
}}

Rules:

impact = 0 to 10

confidence = 0 to 100

direction must be one of:

BULLISH
BEARISH
VOLATILE
NEUTRAL

For every asset use:

BULLISH
BEARISH
VOLATILE
NEUTRAL

Write all explanatory text in Persian.

Be conservative.
Do not invent facts.
Focus on probable market reaction, not certainty.
"""


    payload = json.dumps({

        "inputs": prompt,

        "parameters": {

            "max_new_tokens": 900,

            "temperature": 0.1

        }

    }).encode("utf-8")


    url = (
        "https://router.huggingface.co/"
        "hf-inference/models/"
        "Qwen/Qwen2.5-7B-Instruct"
    )


    request = urllib.request.Request(

        url,

        data=payload,

        method="POST",

        headers={

            "Authorization":
            f"Bearer {HF_TOKEN}",

            "Content-Type":
            "application/json",

            "User-Agent":
            "AI-Market-Radar/4.0"

        }

    )


    try:

        with urllib.request.urlopen(
            request,
            timeout=60
        ) as response:

            raw = response.read().decode(
                "utf-8"
            )


        data = json.loads(raw)


        if isinstance(data, list):

            generated = data[0].get(
                "generated_text",
                ""
            )

        elif isinstance(data, dict):

            generated = data.get(
                "generated_text",
                ""
            )

        else:

            generated = ""


        # Find JSON inside model output

        match = re.search(
            r"\{.*\}",
            generated,
            re.DOTALL
        )


        if not match:

            raise ValueError(
                "AI returned invalid JSON."
            )


        result = json.loads(
            match.group(0)
        )


        return result


    except Exception as error:

        print(
            "AI ANALYST ERROR:",
            error
        )

        return fallback_analysis(
            article
        )


# =========================================================
# FALLBACK ANALYSIS
# =========================================================

def fallback_analysis(article):

    text = (
        article["title"]
        + " "
        + article["description"]
    ).lower()


    impact = calculate_impact(
        article
    )


    if any(
        x in text
        for x in [
            "rate cut",
            "dovish",
            "inflation falls",
            "ceasefire"
        ]
    ):

        direction = "BULLISH"


    elif any(
        x in text
        for x in [
            "rate hike",
            "hawkish",
            "inflation rises",
            "hot cpi",
            "hack"
        ]
    ):

        direction = "BEARISH"


    elif any(
        x in text
        for x in [
            "war",
            "attack",
            "invasion",
            "missile",
            "crisis"
        ]
    ):

        direction = "VOLATILE"


    else:

        direction = "NEUTRAL"


    return {

        "persian_title":
        translate_text(
            article["title"]
        ),

        "summary_fa":
        translate_text(
            article["description"]
        ),

        "impact":
        impact,

        "direction":
        direction,

        "confidence":
        min(
            50 + impact * 4,
            90
        ),

        "time_horizon":
        "کوتاه‌مدت",

        "forex": {

            "EUR/USD":
            "NEUTRAL",

            "GBP/USD":
            "NEUTRAL",

            "USD/JPY":
            "NEUTRAL",

            "DXY":
            "NEUTRAL"

        },

        "crypto": {

            "BTC/USDT":
            direction,

            "ETH/USDT":
            direction

        },

        "commodities": {

            "XAU/USD":
            direction,

            "WTI":
            "NEUTRAL"

        },

        "indices": {

            "NASDAQ":
            direction,

            "SP500":
            direction

        },

        "reason_fa":
        "تحلیل AI در دسترس نبود؛ این نتیجه با موتور تحلیل اولیه تولید شده است."

    }


# =========================================================
# TRANSLATE AI DIRECTION
# =========================================================

def direction_fa(value):

    value = str(
        value or ""
    ).upper()


    if value == "BULLISH":
        return "🟢 صعودی"

    if value == "BEARISH":
        return "🔴 نزولی"

    if value == "VOLATILE":
        return "🟡 نوسانی"

    return "⚪ خنثی"


# =========================================================
# FORMAT TELEGRAM
# =========================================================

def format_ai_alert(
    article,
    analysis
):

    impact = float(
        analysis.get(
            "impact",
            0
        )
    )


    if impact >= 9:

        level = (
            "🚨 هشدار بحرانی بازار"
        )

    elif impact >= 7:

        level = (
            "⚡ هشدار بسیار مهم بازار"
        )

    else:

        level = (
            "📰 هشدار بازار"
        )


    title = analysis.get(
        "persian_title"
    )


    if not title:

        title = translate_text(
            article["title"]
        )


    summary = analysis.get(
        "summary_fa"
    )


    if not summary:

        summary = translate_text(
            article["description"]
        )


    forex = analysis.get(
        "forex",
        {}
    )

    crypto = analysis.get(
        "crypto",
        {}
    )

    commodities = analysis.get(
        "commodities",
        {}
    )

    indices = analysis.get(
        "indices",
        {}
    )


    message = f"""
{level}

📰 {title}

━━━━━━━━━━━━━━━━

📊 شدت اثر:
{impact}/10

🎯 جهت کلی:
{direction_fa(
    analysis.get("direction")
)}

🧠 اطمینان:
{analysis.get(
    "confidence",
    0
)}٪

⏱ افق زمانی:
{analysis.get(
    "time_horizon",
    "نامشخص"
)}

━━━━━━━━━━━━━━━━

💱 FOREX

EUR/USD: {direction_fa(
    forex.get("EUR/USD")
)}

GBP/USD: {direction_fa(
    forex.get("GBP/USD")
)}

USD/JPY: {direction_fa(
    forex.get("USD/JPY")
)}

DXY: {direction_fa(
    forex.get("DXY")
)}

━━━━━━━━━━━━━━━━

₿ CRYPTO

BTC/USDT: {direction_fa(
    crypto.get("BTC/USDT")
)}

ETH/USDT: {direction_fa(
    crypto.get("ETH/USDT")
)}

━━━━━━━━━━━━━━━━

🥇 COMMODITIES

XAU/USD: {direction_fa(
    commodities.get("XAU/USD")
)}

WTI: {direction_fa(
    commodities.get("WTI")
)}

━━━━━━━━━━━━━━━━

📈 INDICES

NASDAQ: {direction_fa(
    indices.get("NASDAQ")
)}

S&P 500: {direction_fa(
    indices.get("SP500")
)}

━━━━━━━━━━━━━━━━

🧠 تحلیل:

{analysis.get(
    "reason_fa",
    ""
)}

━━━━━━━━━━━━━━━━

📝 خلاصه:

{summary}

━━━━━━━━━━━━━━━━

⚠️ تحلیل خودکار است.
این پیام تضمین سود یا توصیه قطعی معامله نیست.

📰 منبع:
{article["link"]}
""".strip()


    return message


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "======================================"
    )

    print(
        "       AI MARKET RADAR STARTED"
    )

    print(
        "======================================"
    )


    state = load_state()


    total = 0

    new_articles = 0

    alerts = 0


    threshold = float(
        CONFIG.get(
            "impact_threshold",
            7
        )
    )


    max_alerts = int(
        CONFIG.get(
            "max_alerts_per_run",
            5
        )
    )


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
                error
            )

            continue


        total += len(
            articles
        )


        for article in articles:

            uid = article_id(
                article
            )


            if uid in state[
                "seen"
            ]:

                continue


            new_articles += 1


            impact = calculate_impact(
                article
            )


            print(
                "--------------------------------"
            )

            print(
                article["title"]
            )

            print(
                f"Initial impact: "
                f"{impact}/10"
            )


            # -----------------------------------------
            # LOW IMPACT
            # -----------------------------------------

            if impact < threshold:

                state[
                    "seen"
                ].append(
                    uid
                )

                continue


            # -----------------------------------------
            # LIMIT
            # -----------------------------------------

            if alerts >= max_alerts:

                continue


            # -----------------------------------------
            # AI
            # -----------------------------------------

            print(
                "Running AI Analyst..."
            )


            analysis = ai_analyze(
                article
            )


            # -----------------------------------------
            # FINAL FILTER
            # -----------------------------------------

            final_impact = float(
                analysis.get(
                    "impact",
                    impact
                )
            )


            if final_impact < threshold:

                state[
                    "seen"
                ].append(
                    uid
                )

                continue


            # -----------------------------------------
            # SEND TELEGRAM
            # -----------------------------------------

            message = format_ai_alert(
                article,
                analysis
            )


            try:

                send_telegram(
                    message
                )


                alerts += 1


                state[
                    "seen"
                ].append(
                    uid
                )


                print(
                    "AI ALERT SENT"
                )


            except Exception as error:

                print(
                    "TELEGRAM ERROR:",
                    error
                )


    save_state(
        state
    )


    print(
        "======================================"
    )

    print(
        f"TOTAL ARTICLES: {total}"
    )

    print(
        f"NEW ARTICLES: {new_articles}"
    )

    print(
        f"AI ALERTS SENT: {alerts}"
    )

    print(
        "======================================")


if __name__ == "__main__":
    main()
