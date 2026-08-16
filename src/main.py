import os
import json
import re
import html
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


# ============================================================
# AI MARKET RADAR v5
# Persian-First Market & Whale Intelligence
# ============================================================

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None


# ============================================================
# ENVIRONMENT
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()

HF_TOKEN = os.getenv("HF_TOKEN", "").strip()

AI_MODEL = os.getenv(
    "AI_MODEL",
    "Qwen/Qwen3-4B-Instruct-2507"
).strip()


# ============================================================
# VALIDATION
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is missing"
    )

if not CHAT_ID:
    raise RuntimeError(
        "TELEGRAM_CHAT_ID is missing"
    )


# ============================================================
# CONFIG
# ============================================================

with open(
    "config.json",
    encoding="utf-8"
) as f:

    CONFIG = json.load(f)


# ============================================================
# TEXT
# ============================================================

def clean_text(text):

    text = html.unescape(
        text or ""
    )

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


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(
    message,
    target
):

    if not target:
        return

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    payload = urllib.parse.urlencode({

        "chat_id":
        target,

        "text":
        message,

        "disable_web_page_preview":
        "true"

    }).encode()

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
            response.read().decode()
        )

    if not result.get("ok"):

        raise RuntimeError(
            f"Telegram error: {result}"
        )


def broadcast(message):

    # ارسال به چت شخصی
    send_telegram(
        message,
        CHAT_ID
    )

    # ارسال به کانال
    if CHANNEL_ID:

        send_telegram(
            message,
            CHANNEL_ID
        )


# ============================================================
# HTTP
# ============================================================

def fetch_url(url):

    request = urllib.request.Request(

        url,

        headers={
            "User-Agent":
            "AI-Market-Radar/5.0"
        }

    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return response.read()


# ============================================================
# RSS
# ============================================================

def parse_rss(
    data,
    source
):

    root = ET.fromstring(
        data
    )

    articles = []

    for item in root.findall(
        ".//item"
    ):

        title = clean_text(
            item.findtext("title")
        )

        link = (
            item.findtext("link")
            or ""
        ).strip()

        description = clean_text(
            item.findtext(
                "description"
            )
        )

        published = clean_text(
            item.findtext(
                "pubDate"
            )
        )

        if not title or not link:
            continue

        articles.append({

            "title":
            title,

            "link":
            link,

            "description":
            description,

            "published":
            published,

            "source":
            source

        })

    return articles


# ============================================================
# STATE
# ============================================================

def load_state():

    try:

        with open(
            "state.json",
            encoding="utf-8"
        ) as f:

            state = json.load(f)

            if isinstance(
                state,
                dict
            ):

                return state

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
        )
    )[-5000:]

    with open(
        "state.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def article_id(
    article
):

    raw = (
        article["title"]
        + "|"
        + article["link"]
    )

    return hashlib.sha256(
        raw.encode()
    ).hexdigest()


# ============================================================
# NEWS IMPORTANCE ENGINE
# ============================================================

KEYWORDS = {

    # CENTRAL BANKS
    "federal reserve": 3.0,
    "fed": 2.5,
    "fomc": 3.0,
    "ecb": 2.5,
    "boj": 2.5,
    "boe": 2.5,

    # RATES
    "interest rate": 2.5,
    "rate hike": 3.0,
    "rate cut": 3.0,

    # ECONOMIC DATA
    "inflation": 2.5,
    "cpi": 3.0,
    "pce": 3.0,
    "nfp": 3.0,
    "nonfarm payroll": 3.0,
    "unemployment": 2.0,
    "gdp": 2.0,
    "pmi": 2.0,

    # BONDS
    "treasury yield": 2.5,
    "10-year yield": 2.5,
    "bond yield": 2.5,

    # CRYPTO
    "bitcoin": 2.0,
    "btc": 2.0,
    "ethereum": 1.5,
    "eth": 1.5,
    "crypto": 1.5,
    "stablecoin": 1.5,
    "bitcoin etf": 3.0,

    # COMMODITIES
    "gold": 1.5,
    "oil": 1.5,
    "crude": 1.5,
    "opec": 2.5,

    # GEOPOLITICS
    "war": 3.0,
    "attack": 3.0,
    "missile": 3.0,
    "invasion": 3.0,
    "ceasefire": 2.5,
    "conflict": 2.5,
    "sanctions": 2.0,
    "tariff": 2.5,
    "trade war": 3.0,

    # FINANCIAL CRISIS
    "bank failure": 3.0,
    "bankruptcy": 3.0,
    "default": 3.0,
    "banking crisis": 3.0,

    # SECURITY
    "hack": 2.5,
    "exploit": 2.5,

    # BREAKING
    "breaking": 1.0,
    "urgent": 1.0,
    "just in": 1.0
}


def calculate_importance(
    article
):

    text = (
        article["title"]
        + " "
        + article["description"]
    ).lower()

    total = 0

    for keyword, weight in KEYWORDS.items():

        if keyword in text:

            total += weight

    return min(
        10.0,
        round(total, 1)
    )


# ============================================================
# ALERT LEVEL
# ============================================================

def get_level(score):

    if score >= 8.5:

        return (
            "🔴",
            "سطح ۳",
            "هشدار معاملاتی"
        )

    if score >= 6.0:

        return (
            "🟠",
            "سطح ۲",
            "هشدار بازار"
        )

    return (
        "🟢",
        "سطح ۱",
        "اطلاع‌رسانی"
    )


# ============================================================
# DIRECTION
# ============================================================

def direction_fa(
    value
):

    directions = {

        "BULLISH":
        "🟢 صعودی",

        "BEARISH":
        "🔴 نزولی",

        "VOLATILE":
        "🟡 نوسانی",

        "NEUTRAL":
        "⚪ خنثی"

    }

    return directions.get(
        str(value).upper(),
        "⚪ خنثی"
    )


# ============================================================
# AI SCHEMA
# ============================================================

AI_SCHEMA = {

    "type":
    "object",

    "properties": {

        "title_fa":
        {
            "type":
            "string"
        },

        "simple_summary":
        {
            "type":
            "string"
        },

        "impact":
        {
            "type":
            "number"
        },

        "confidence":
        {
            "type":
            "number"
        },

        "direction":
        {

            "type":
            "string",

            "enum":
            [
                "BULLISH",
                "BEARISH",
                "VOLATILE",
                "NEUTRAL"
            ]

        },

        "horizon":
        {
            "type":
            "string"
        },

        "why":
        {
            "type":
            "string"
        },

        "watch":
        {
            "type":
            "string"
        },

        "invalidation":
        {
            "type":
            "string"
        },

        "forex":
        {
            "type":
            "string"
        },

        "crypto":
        {
            "type":
            "string"
        },

        "commodities":
        {
            "type":
            "string"
        },

        "indices":
        {
            "type":
            "string"
        }

    },

    "required":
    [

        "title_fa",
        "simple_summary",
        "impact",
        "confidence",
        "direction",
        "horizon",
        "why",
        "watch",
        "invalidation",
        "forex",
        "crypto",
        "commodities",
        "indices"

    ]

}


# ============================================================
# AI ANALYST
# ============================================================

def ai_analyze(
    article,
    base_score
):

    if not HF_TOKEN:
        return None

    if InferenceClient is None:
        return None

    prompt = f"""

تو تحلیلگر ارشد بازارهای مالی هستی.

کاربر فارسی‌زبان است.

خبر:

عنوان:
{article["title"]}

خلاصه:
{article["description"]}

منبع:
{article["source"]}

امتیاز اولیه:
{base_score}/10

خبر را تحلیل کن.

بازارهای زیر را بررسی کن:

DXY
EUR/USD
GBP/USD
USD/JPY

BTC
ETH

GOLD
OIL

NASDAQ
S&P 500

برای هر بازار فقط در صورت وجود شواهد
جهت احتمالی را مشخص کن.

گزینه‌ها:

BULLISH
BEARISH
VOLATILE
NEUTRAL

همچنین مشخص کن:

- چرا خبر مهم است؟
- معنی ساده خبر چیست؟
- اثر احتمالی روی بازار چیست؟
- معامله‌گر چه چیزی را زیر نظر بگیرد؟
- چه چیزی سناریو را باطل می‌کند؟
- شدت اثر از 0 تا 10
- میزان اطمینان از 0 تا 100
- بازه زمانی اثر

اثر احتمالی را هیچ‌وقت قطعی معرفی نکن.

همه توضیحات فارسی باشند.

"""


    try:

        client = InferenceClient(

            provider="auto",

            api_key=HF_TOKEN

        )

        response = client.chat_completion(

            model=AI_MODEL,

            messages=[

                {

                    "role":
                    "system",

                    "content":
                    (
                        "تو یک تحلیلگر حرفه‌ای "
                        "بازار مالی فارسی‌زبان هستی. "
                        "اطلاعات ساختگی تولید نکن."
                    )

                },

                {

                    "role":
                    "user",

                    "content":
                    prompt

                }

            ],

            response_format={

                "type":
                "json_schema",

                "json_schema": {

                    "name":
                    "MarketAnalysis",

                    "schema":
                    AI_SCHEMA,

                    "strict":
                    True

                }

            },

            temperature=0.1,

            max_tokens=1400

        )

        return json.loads(

            response
            .choices[0]
            .message
            .content

        )

    except Exception as error:

        print(
            "AI ERROR:",
            error
        )

        return None


# ============================================================
# FALLBACK
# ============================================================

def fallback_analysis(
    article,
    score
):

    return {

        "title_fa":
        article["title"],

        "simple_summary":
        (
            article["description"][:700]
            or
            "خبر مهمی شناسایی شده است."
        ),

        "impact":
        score,

        "confidence":
        min(
            65,
            35 + score * 3
        ),

        "direction":
        (
            "VOLATILE"
            if score >= 7
            else "NEUTRAL"
        ),

        "horizon":
        "کوتاه‌مدت",

        "why":
        (
            "این خبر به دلیل ارتباط "
            "با بازارهای مالی مهم "
            "توسط موتور رادار شناسایی شده است."
        ),

        "watch":
        (
            "DXY، بازده اوراق، BTC، "
            "NASDAQ و حجم معاملات"
        ),

        "invalidation":
        (
            "واکنش معکوس قیمت یا "
            "تکذیب خبر می‌تواند سناریو "
            "را ضعیف کند."
        ),

        "forex":
        "⚪ نیازمند تأیید",

        "crypto":
        "🟡 نوسانی",

        "commodities":
        "⚪ نیازمند تأیید",

        "indices":
        "🟡 نوسانی"

    }


# ============================================================
# NEWS MESSAGE
# ============================================================

def build_news_message(
    article,
    analysis
):

    impact = float(
        analysis["impact"]
    )

    icon, level, label = get_level(
        impact
    )

    return f"""

━━━━━━━━━━━━━━━━━━━━
{icon} {level} | {label}
━━━━━━━━━━━━━━━━━━━━

📰 {analysis["title_fa"]}

📊 شدت تأثیر:
{impact:.1f} از 10

🎯 میزان اطمینان:
{float(analysis["confidence"]):.0f}٪

🎯 جهت احتمالی:
{direction_fa(
    analysis["direction"]
)}

⏱ بازه اثر:
{analysis["horizon"]}

━━━━━━━━━━━━━━━━━━━━
🧠 تحلیل هوشمند بازار
━━━━━━━━━━━━━━━━━━━━

❓ چرا مهم است؟

{analysis["why"]}

📖 معنی ساده:

{analysis["simple_summary"]}

━━━━━━━━━━━━━━━━━━━━
📈 اثر احتمالی بازار
━━━━━━━━━━━━━━━━━━━━

💱 فارکس:

{analysis["forex"]}

₿ کریپتو:

{analysis["crypto"]}

🥇 کالاها:

{analysis["commodities"]}

📊 شاخص‌ها:

{analysis["indices"]}

━━━━━━━━━━━━━━━━━━━━
👀 چه چیزی را زیر نظر بگیریم؟
━━━━━━━━━━━━━━━━━━━━

{analysis["watch"]}

━━━━━━━━━━━━━━━━━━━━
⚠️ نقطه ابطال سناریو
━━━━━━━━━━━━━━━━━━━━

{analysis["invalidation"]}

━━━━━━━━━━━━━━━━━━━━

📰 منبع:
{article["source"]}

🔗 {article["link"]}

⚠️ این تحلیل احتمالی است،
نه تضمین سود یا معامله.
"""


# ============================================================
# WHALE INTELLIGENCE
# ============================================================

WHALE_MIN_USD = float(
    CONFIG.get(
        "whale_min_usd",
        10000000
    )
)

WHALE_L2_USD = float(
    CONFIG.get(
        "whale_l2_usd",
        50000000
    )
)


def whale_level(
    value_usd
):

    if value_usd >= WHALE_L2_USD:

        return (
            "🔴",
            "سطح ۲",
            "هشدار نهنگ"
        )

    if value_usd >= WHALE_MIN_USD:

        return (
            "🟡",
            "سطح ۱",
            "فعالیت مهم نهنگ"
        )

    return None


def whale_direction(
    transaction
):

    direction = str(
        transaction.get(
            "direction",
            ""
        )
    ).lower()

    if direction in [
        "exchange_in",
        "deposit"
    ]:

        return (
            "🔴",
            "ورود به صرافی",
            "احتمال افزایش فشار فروش"
        )

    if direction in [
        "exchange_out",
        "withdrawal"
    ]:

        return (
            "🟢",
            "خروج از صرافی",
            "احتمال کاهش فشار فروش"
        )

    return (
        "🟡",
        "انتقال بین کیف‌پول‌ها",
        "جهت معامله مشخص نیست"
    )


def build_whale_message(
    transaction
):

    value_usd = float(
        transaction.get(
            "value_usd",
            0
        ) or 0
    )

    level_data = whale_level(
        value_usd
    )

    if not level_data:
        return None

    icon, level, label = level_data

    (
        direction_icon,
        direction_name,
        direction_meaning
    ) = whale_direction(
        transaction
    )

    symbol = transaction.get(
        "symbol",
        "نامشخص"
    )

    amount = transaction.get(
        "amount",
        "نامشخص"
    )

    owner = transaction.get(
        "owner",
        "نهنگ ناشناس"
    )

    from_owner = transaction.get(
        "from_owner",
        "نامشخص"
    )

    to_owner = transaction.get(
        "to_owner",
        "نامشخص"
    )

    tx_hash = transaction.get(
        "tx_hash",
        ""
    )

    return f"""

━━━━━━━━━━━━━━━━━━━━
🐋 {icon} {level} | {label}
━━━━━━━━━━━━━━━━━━━━

👤 نهنگ:

{owner}

━━━━━━━━━━━━━━━━━━━━

💰 دارایی:

{symbol}

🔢 مقدار:

{amount}

💵 ارزش تقریبی:

${value_usd:,.0f}

━━━━━━━━━━━━━━━━━━━━
🔄 مسیر تراکنش
━━━━━━━━━━━━━━━━━━━━

📤 مبدأ:

{from_owner}

📥 مقصد:

{to_owner}

━━━━━━━━━━━━━━━━━━━━
📊 برداشت اولیه رادار
━━━━━━━━━━━━━━━━━━━━

{direction_icon} وضعیت:

{direction_name}

🧠 معنی ساده:

{direction_meaning}

━━━━━━━━━━━━━━━━━━━━
🧠 تحلیل AI
━━━━━━━━━━━━━━━━━━━━

این انتقال به دلیل حجم بالا
توسط سیستم Whale Intelligence
شناسایی شده است.

⚠️ انتقال بزرگ به‌تنهایی
به معنی خرید یا فروش قطعی نیست.

جهت واقعی باید با:

قیمت
حجم معاملات
جریان صرافی‌ها
و رفتار بازار

تأیید شود.

━━━━━━━━━━━━━━━━━━━━

🔗 TX:

{tx_hash}

⚠️ هشدار نهنگ، سیگنال قطعی
خرید یا فروش نیست.
"""


# ============================================================
# WHALE FEED
# ============================================================

def process_whale_feed(
    state
):

    feed_url = CONFIG.get(
        "whale_feed_url",
        ""
    ).strip()

    if not feed_url:

        print(
            "Whale feed: not configured"
        )

        return 0

    try:

        raw = fetch_url(
            feed_url
        )

        data = json.loads(
            raw.decode()
        )

    except Exception as error:

        print(
            "WHALE FEED ERROR:",
            error
        )

        return 0

    if isinstance(
        data,
        list
    ):

        transactions = data

    else:

        transactions = data.get(
            "transactions",
            []
        )

    sent = 0

    maximum = int(
        CONFIG.get(
            "whale_max_per_run",
            5
        )
    )

    for transaction in transactions:

        if sent >= maximum:
            break

        transaction_id = hashlib.sha256(

            json.dumps(
                transaction,
                sort_keys=True
            ).encode()

        ).hexdigest()

        if transaction_id in state["seen"]:

            continue

        value = float(
            transaction.get(
                "value_usd",
                0
            ) or 0
        )

        if value < WHALE_MIN_USD:

            state["seen"].append(
                transaction_id
            )

            continue

        message = build_whale_message(
            transaction
        )

        if not message:

            continue

        broadcast(
            message
        )

        state["seen"].append(
            transaction_id
        )

        sent += 1

    return sent


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "======================================"
    )

    print(
        "       AI MARKET RADAR v5"
    )

    print(
        "======================================"
    )

    state = load_state()

    total_articles = 0

    new_articles = 0

    alerts_sent = 0

    whale_alerts = 0

    feeds = CONFIG.get(
        "feeds",
        []
    )

    # ========================================================
    # NEWS
    # ========================================================

    for feed in feeds:

        try:

            data = fetch_url(
                feed["url"]
            )

            articles = parse_rss(
                data,
                feed["name"]
            )

            print(
                "Feed:",
                feed["name"],
                "Articles:",
                len(articles)
            )

        except Exception as error:

            print(
                "FEED ERROR:",
                feed["name"],
                error
            )

            continue

        total_articles += len(
            articles
        )

        for article in articles:

            identifier = article_id(
                article
            )

            if identifier in state["seen"]:

                continue

            new_articles += 1

            state["seen"].append(
                identifier
            )

            base_score = calculate_importance(
                article
            )

            minimum_score = float(
                CONFIG.get(
                    "news_min_score",
                    4.0
                )
            )

            if base_score < minimum_score:

                continue

            analysis = ai_analyze(
                article,
                base_score
            )

            if not analysis:

                analysis = fallback_analysis(
                    article,
                    base_score
                )

            final_score = float(
                analysis["impact"]
            )

            alert_minimum = float(
                CONFIG.get(
                    "alert_min_score",
                    5.5
                )
            )

            if final_score < alert_minimum:

                continue

            maximum_alerts = int(
                CONFIG.get(
                    "max_alerts_per_run",
                    8
                )
            )

            if alerts_sent >= maximum_alerts:

                continue

            message = build_news_message(
                article,
                analysis
            )

            broadcast(
                message
            )

            alerts_sent += 1

    # ========================================================
    # WHALES
    # ========================================================

    whale_alerts = process_whale_feed(
        state
    )

    # ========================================================
    # SAVE
    # ========================================================

    save_state(
        state
    )

    # ========================================================
    # REPORT
    # ========================================================

    print(
        "======================================"
    )

    print(
        "TOTAL ARTICLES:",
        total_articles
    )

    print(
        "NEW ARTICLES:",
        new_articles
    )

    print(
        "NEWS ALERTS SENT:",
        alerts_sent
    )

    print(
        "WHALE ALERTS SENT:",
        whale_alerts
    )

    print(
        "======================================"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
