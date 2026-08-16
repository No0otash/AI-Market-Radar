import os
import json
import re
import html
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


# ============================================================
# AI MARKET RADAR
# NEWS + AI + WHALE ALERT
# ============================================================

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None


# ============================================================
# ENV
# ============================================================

BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", ""
).strip()

CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID", ""
).strip()

CHANNEL_ID = os.getenv(
    "TELEGRAM_CHANNEL_ID", ""
).strip()

HF_TOKEN = os.getenv(
    "HF_TOKEN", ""
).strip()

WHALE_ALERT_API_KEY = os.getenv(
    "WHALE_ALERT_API_KEY", ""
).strip()

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

WHALE_MAX_PER_RUN = int(
    CONFIG.get(
        "whale_max_per_run",
        5
    )
)


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
        "https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    data = urllib.parse.urlencode({
        "chat_id": target,
        "text": message,
        "disable_web_page_preview": "true"
    }).encode()

    request = urllib.request.Request(
        url,
        data=data,
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

    send_telegram(
        message,
        CHAT_ID
    )

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
            "AI-Market-Radar/1.0"
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

        if not title or not link:
            continue

        articles.append({

            "title": title,

            "link": link,

            "description":
            description,

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

            return json.load(f)

    except Exception:

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
# ID
# ============================================================

def make_id(text):

    return hashlib.sha256(
        text.encode()
    ).hexdigest()


# ============================================================
# NEWS SCORING
# ============================================================

KEYWORDS = {

    "federal reserve": 3,
    "fed": 2,
    "fomc": 3,
    "ecb": 2,
    "boj": 2,

    "interest rate": 3,
    "rate hike": 3,
    "rate cut": 3,

    "inflation": 2,
    "cpi": 3,
    "pce": 3,
    "nfp": 3,
    "unemployment": 2,
    "gdp": 2,

    "treasury yield": 3,
    "bond yield": 2,

    "bitcoin": 2,
    "btc": 2,
    "ethereum": 2,
    "eth": 2,
    "crypto": 1,

    "gold": 2,
    "oil": 2,
    "opec": 3,

    "war": 3,
    "attack": 3,
    "missile": 3,
    "invasion": 3,
    "sanctions": 2,
    "tariff": 2,
    "trade war": 3,

    "bank failure": 3,
    "default": 3,
    "bankruptcy": 3
}


def calculate_score(article):

    text = (
        article["title"]
        + " "
        + article["description"]
    ).lower()

    score = 0

    for keyword, weight in KEYWORDS.items():

        if keyword in text:
            score += weight

    return min(
        10,
        score
    )


# ============================================================
# AI
# ============================================================

def ai_analyze(
    article,
    score
):

    if not HF_TOKEN:
        return None

    if InferenceClient is None:
        return None

    prompt = f"""

تو تحلیلگر ارشد بازارهای مالی هستی.

خبر:

{article["title"]}

{article["description"]}

امتیاز اولیه:
{score}/10

به فارسی تحلیل کن.

مشخص کن:

- خلاصه ساده
- دلیل اهمیت
- اثر روی دلار
- اثر روی BTC
- اثر روی طلا
- اثر روی نفت
- اثر روی NASDAQ
- جهت احتمالی
- بازه زمانی
- میزان اطمینان

اثر احتمالی را قطعی معرفی نکن.

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
                    "تحلیلگر مالی فارسی‌زبان باش."
                },

                {
                    "role":
                    "user",

                    "content":
                    prompt
                }

            ],

            temperature=0.1,

            max_tokens=1000
        )

        return (
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
# NEWS MESSAGE
# ============================================================

def build_news_message(
    article,
    score,
    analysis
):

    if score >= 8:

        level = "🔴 سطح ۳"

    elif score >= 6:

        level = "🟠 سطح ۲"

    else:

        level = "🟢 سطح ۱"

    ai_text = (
        analysis
        if analysis
        else
        "تحلیل AI در دسترس نیست."
    )

    return f"""

━━━━━━━━━━━━━━━━━━━━
{level} | AI MARKET RADAR
━━━━━━━━━━━━━━━━━━━━

📰 {article["title"]}

📊 اهمیت:
{score}/10

━━━━━━━━━━━━━━━━━━━━
🧠 تحلیل هوشمند
━━━━━━━━━━━━━━━━━━━━

{ai_text}

━━━━━━━━━━━━━━━━━━━━

📰 منبع:
{article["source"]}

🔗 {article["link"]}

⚠️ این تحلیل احتمالی است
و تضمین معامله نیست.
"""


# ============================================================
# WHALE ALERT API
# ============================================================

def fetch_whale_alerts():

    if not WHALE_ALERT_API_KEY:

        print(
            "WHALE_ALERT_API_KEY missing"
        )

        return []

    url = (
        "https://api.whale-alert.io/v1/"
        "transactions"
    )

    params = {

        "api_key":
        WHALE_ALERT_API_KEY,

        "min_value":
        int(WHALE_MIN_USD),

        "limit":
        WHALE_MAX_PER_RUN

    }

    full_url = (
        url
        + "?"
        + urllib.parse.urlencode(
            params
        )
    )

    try:

        raw = fetch_url(
            full_url
        )

        data = json.loads(
            raw.decode()
        )

        if data.get(
            "result"
        ) != "success":

            print(
                "WHALE ALERT API:",
                data
            )

            return []

        return data.get(
            "transactions",
            []
        )

    except Exception as error:

        print(
            "WHALE ALERT ERROR:",
            error
        )

        return []


# ============================================================
# WHALE FORMAT
# ============================================================

def format_whale_alert(
    tx
):

    amount = float(
        tx.get(
            "amount",
            0
        ) or 0
    )

    amount_usd = float(
        tx.get(
            "amount_usd",
            0
        ) or 0
    )

    symbol = tx.get(
        "symbol",
        "UNKNOWN"
    )

    blockchain = tx.get(
        "blockchain",
        "Unknown"
    )

    tx_hash = tx.get(
        "hash",
        ""
    )

    sender = tx.get(
        "from",
        {}
    )

    receiver = tx.get(
        "to",
        {}
    )

    sender_owner = (
        sender.get(
            "owner",
            "Unknown"
        )
        if isinstance(
            sender,
            dict
        )
        else "Unknown"
    )

    receiver_owner = (
        receiver.get(
            "owner",
            "Unknown"
        )
        if isinstance(
            receiver,
            dict
        )
        else "Unknown"
    )

    if amount_usd >= WHALE_L2_USD:

        level = (
            "🔴 سطح ۲ | "
            "هشدار نهنگ"
        )

    else:

        level = (
            "🟡 سطح ۱ | "
            "فعالیت نهنگ"
        )

    if (
        sender_owner != "Unknown"
        and
        receiver_owner == "Unknown"
    ):

        interpretation = (
            "خروج دارایی از یک نهاد "
            "شناخته‌شده به مقصد ناشناس."
        )

    elif (
        sender_owner == "Unknown"
        and
        receiver_owner != "Unknown"
    ):

        interpretation = (
            "ورود دارایی به یک نهاد "
            "شناخته‌شده."
        )

    else:

        interpretation = (
            "انتقال بزرگ شناسایی شد؛ "
            "جهت معامله به‌تنهایی مشخص نیست."
        )

    return f"""

━━━━━━━━━━━━━━━━━━━━
🐋 {level}
━━━━━━━━━━━━━━━━━━━━

💰 دارایی:
{symbol}

🔢 مقدار:
{amount:,.4f}

💵 ارزش:
${amount_usd:,.0f}

⛓ بلاکچین:
{blockchain}

━━━━━━━━━━━━━━━━━━━━
👤 طرفین تراکنش
━━━━━━━━━━━━━━━━━━━━

📤 مبدأ:
{sender_owner}

📥 مقصد:
{receiver_owner}

━━━━━━━━━━━━━━━━━━━━
🧠 برداشت رادار
━━━━━━━━━━━━━━━━━━━━

{interpretation}

⚠️ انتقال بزرگ به‌تنهایی
به معنی خرید یا فروش قطعی نیست.

━━━━━━━━━━━━━━━━━━━━
🔗 Transaction
━━━━━━━━━━━━━━━━━━━━

{tx_hash}

⚠️ Whale Alert سیگنال قطعی
خرید یا فروش نیست.
"""


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "================================"
    )

    print(
        "     AI MARKET RADAR"
    )

    print(
        "================================"
    )

    state = load_state()

    total_articles = 0

    new_articles = 0

    news_alerts = 0

    whale_alerts = 0

    # ========================================================
    # NEWS
    # ========================================================

    for feed in CONFIG.get(
        "feeds",
        []
    ):

        try:

            data = fetch_url(
                feed["url"]
            )

            articles = parse_rss(
                data,
                feed["name"]
            )

            print(
                "Articles:",
                len(articles),
                "|",
                feed["name"]
            )

        except Exception as error:

            print(
                "FEED ERROR:",
                error
            )

            continue

        total_articles += len(
            articles
        )

        for article in articles:

            identifier = make_id(
                article["link"]
            )

            if identifier in state["seen"]:
                continue

            state["seen"].append(
                identifier
            )

            new_articles += 1

            score = calculate_score(
                article
            )

            if score < float(
                CONFIG.get(
                    "news_min_score",
                    3.5
                )
            ):
                continue

            analysis = ai_analyze(
                article,
                score
            )

            if score >= float(
                CONFIG.get(
                    "alert_min_score",
                    5.5
                )
            ):

                message = build_news_message(
                    article,
                    score,
                    analysis
                )

                broadcast(
                    message
                )

                news_alerts += 1

                if news_alerts >= int(
                    CONFIG.get(
                        "max_alerts_per_run",
                        8
                    )
                ):
                    break

    # ========================================================
    # WHALE ALERT
    # ========================================================

    whale_transactions = (
        fetch_whale_alerts()
    )

    for tx in whale_transactions:

        tx_hash = tx.get(
            "hash",
            ""
        )

        if not tx_hash:
            continue

        identifier = make_id(
            "WHALE|" + tx_hash
        )

        if identifier in state["seen"]:
            continue

        state["seen"].append(
            identifier
        )

        message = format_whale_alert(
            tx
        )

        broadcast(
            message
        )

        whale_alerts += 1

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
        "================================"
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
        "NEWS ALERTS:",
        news_alerts
    )

    print(
        "WHALE ALERTS:",
        whale_alerts
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    main()
