import os
import json
import re
import html
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET


# ============================================================
# AI MARKET RADAR
# NEWS + AI + WHALE ALERT + TELEGRAM
# ============================================================


try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    ""
).strip()

CHANNEL_ID = os.getenv(
    "TELEGRAM_CHANNEL_ID",
    ""
).strip()

HF_TOKEN = os.getenv(
    "HF_TOKEN",
    ""
).strip()

WHALE_ALERT_API_KEY = os.getenv(
    "WHALE_ALERT_API_KEY",
    ""
).strip()

AI_MODEL = os.getenv(
    "AI_MODEL",
    "Qwen/Qwen3-4B-Instruct-2507"
).strip()


# ============================================================
# BASIC VALIDATION
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

try:

    with open(
        "config.json",
        encoding="utf-8"
    ) as f:

        CONFIG = json.load(f)

except Exception as error:

    raise RuntimeError(
        f"Unable to load config.json: {error}"
    )


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
# TEXT CLEANER
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
# TELEGRAM TARGET CLEANER
# ============================================================

def clean_telegram_target(target):

    if not target:
        return ""

    target = str(target).strip()

    target = (
        target
        .strip("\"'")
        .replace("\r", "")
        .replace("\n", "")
        .strip()
    )

    # Convert accidental t.me/username format
    if target.startswith(
        "https://t.me/"
    ):

        target = (
            "@"
            + target.split(
                "https://t.me/",
                1
            )[1].strip("/")
        )

    elif target.startswith(
        "http://t.me/"
    ):

        target = (
            "@"
            + target.split(
                "http://t.me/",
                1
            )[1].strip("/")
        )

    elif target.startswith(
        "t.me/"
    ):

        target = (
            "@"
            + target.split(
                "t.me/",
                1
            )[1].strip("/")
        )

    return target


# ============================================================
# TELEGRAM SEND
# ============================================================

def send_telegram(
    message,
    target,
    target_name="Telegram"
):

    target = clean_telegram_target(
        target
    )

    if not target:

        raise RuntimeError(
            f"{target_name}: target is empty"
        )


    if not message:

        raise RuntimeError(
            f"{target_name}: message is empty"
        )


    url = (
        "https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )


    data = urllib.parse.urlencode({

        "chat_id":
        target,

        "text":
        message,

        "disable_web_page_preview":
        "true"

    }).encode(
        "utf-8"
    )


    request = urllib.request.Request(

        url,

        data=data,

        method="POST",

        headers={

            "Content-Type":
            "application/x-www-form-urlencoded; "
            "charset=UTF-8",

            "User-Agent":
            "AI-Market-Radar/2.0"

        }
    )


    try:

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            raw_response = (
                response
                .read()
                .decode(
                    "utf-8",
                    errors="replace"
                )
            )


    except urllib.error.HTTPError as error:

        error_body = ""

        try:

            error_body = (
                error
                .read()
                .decode(
                    "utf-8",
                    errors="replace"
                )
            )

        except Exception:

            pass


        raise RuntimeError(
            f"{target_name} Telegram "
            f"HTTP {error.code}: "
            f"{error_body}"
        ) from error


    except Exception as error:

        raise RuntimeError(
            f"{target_name} Telegram "
            f"connection error: {error}"
        ) from error


    try:

        result = json.loads(
            raw_response
        )

    except json.JSONDecodeError:

        raise RuntimeError(
            f"{target_name}: invalid "
            f"Telegram response: "
            f"{raw_response[:500]}"
        )


    if not result.get(
        "ok"
    ):

        raise RuntimeError(
            f"{target_name}: Telegram API "
            f"rejected message: "
            f"{result}"
        )


    return result


# ============================================================
# BROADCAST
# ============================================================

def broadcast(message):

    print("")
    print(
        "================================"
    )

    print(
        "TELEGRAM BROADCAST"
    )

    print(
        "================================"
    )


    # --------------------------------------------------------
    # PERSONAL CHAT
    # --------------------------------------------------------

    try:

        result = send_telegram(

            message,

            CHAT_ID,

            "Personal Chat"

        )


        message_id = (
            result
            .get(
                "result",
                {}
            )
            .get(
                "message_id",
                "unknown"
            )
        )


        print(
            "PERSONAL CHAT: OK"
        )

        print(
            "Personal message_id:",
            message_id
        )


    except Exception as error:

        print(
            "PERSONAL CHAT ERROR:"
        )

        print(
            error
        )


    # --------------------------------------------------------
    # CHANNEL
    # --------------------------------------------------------

    if not CHANNEL_ID:

        print(
            "CHANNEL: NOT CONFIGURED"
        )

        print(
            "TELEGRAM_CHANNEL_ID is empty"
        )

        print(
            "================================"
        )

        return


    channel_target = (
        clean_telegram_target(
            CHANNEL_ID
        )
    )


    print(
        "Channel target:",
        channel_target
    )


    try:

        result = send_telegram(

            message,

            channel_target,

            "Channel"

        )


        message_id = (
            result
            .get(
                "result",
                {}
            )
            .get(
                "message_id",
                "unknown"
            )
        )


        print(
            "CHANNEL: OK"
        )

        print(
            "Channel message_id:",
            message_id
        )


    except Exception as error:

        print(
            "CHANNEL ERROR:"
        )

        print(
            error
        )


    print(
        "================================"
    )


# ============================================================
# HTTP FETCH
# ============================================================

def fetch_url(url):

    request = urllib.request.Request(

        url,

        headers={

            "User-Agent":
            "Mozilla/5.0 "
            "(compatible; AI-Market-Radar/2.0)",

            "Accept":
            "application/rss+xml, "
            "application/xml, "
            "text/xml, "
            "application/json, "
            "*/*"

        }
    )


    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return response.read()


# ============================================================
# RSS PARSER
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
            item.findtext(
                "title"
            )
        )


        link = (
            item.findtext(
                "link"
            )
            or ""
        ).strip()


        description = clean_text(
            item.findtext(
                "description"
            )
        )


        if not title:

            continue


        articles.append({

            "title":
            title,

            "link":
            link,

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

            state = json.load(
                f
            )


        if "seen" not in state:

            state["seen"] = []


        return state


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
# HASH ID
# ============================================================

def make_id(text):

    return hashlib.sha256(
        text.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# NEWS KEYWORDS
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


# ============================================================
# NEWS SCORE
# ============================================================

def calculate_score(
    article
):

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
# AI ANALYSIS
# ============================================================

def ai_analyze(
    article,
    score
):

    if not HF_TOKEN:

        print(
            "HF_TOKEN missing - "
            "using fallback analysis"
        )

        return None


    if InferenceClient is None:

        print(
            "huggingface_hub unavailable"
        )

        return None


    prompt = f"""

تو یک تحلیلگر ارشد بازارهای مالی
و ارز دیجیتال هستی.

خبر:

{article["title"]}

{article["description"]}

امتیاز اولیه:
{score}/10

لطفاً تحلیل کاملاً فارسی،
روان و قابل فهم برای افراد
غیرمسلط به زبان انگلیسی ارائه بده.

ساختار پاسخ:

📌 خلاصه خبر

🎯 چرا مهم است؟

📈 اثر احتمالی روی بیت‌کوین BTC

💵 اثر احتمالی روی دلار

🥇 اثر احتمالی روی طلا

🛢 اثر احتمالی روی نفت

📊 اثر احتمالی روی بازار سهام

🧭 جهت احتمالی بازار

⏱ بازه زمانی اثر

🎯 میزان اطمینان

⚠️ هشدار ریسک

هیچ نتیجه‌ای را قطعی معرفی نکن.
سیگنال خرید یا فروش قطعی صادر نکن.

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
                    "تو تحلیلگر حرفه‌ای "
                    "بازارهای مالی هستی. "
                    "باید فارسی، واضح، "
                    "ساده و مسئولانه "
                    "پاسخ بدهی."

                },

                {

                    "role":
                    "user",

                    "content":
                    prompt

                }

            ],

            temperature=0.1,

            max_tokens=1200

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

        level = (
            "🔴 سطح ۳ | بسیار مهم"
        )

    elif score >= 6:

        level = (
            "🟠 سطح ۲ | مهم"
        )

    else:

        level = (
            "🟢 سطح ۱ | قابل توجه"
        )


    ai_text = (

        analysis

        if analysis

        else

        "تحلیل AI در دسترس نیست."

    )


    return f"""
━━━━━━━━━━━━━━━━━━━━
🤖 AI MARKET RADAR
{level}
━━━━━━━━━━━━━━━━━━━━

📰 خبر:

{article["title"]}

📊 امتیاز اهمیت:
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
و تضمین سود یا سیگنال قطعی
خرید و فروش نیست.

━━━━━━━━━━━━━━━━━━━━
"""


# ============================================================
# WHALE ALERT
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
        int(
            WHALE_MIN_USD
        ),

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
            raw.decode(
                "utf-8"
            )
        )


        if data.get(
            "result"
        ) != "success":

            print(
                "WHALE ALERT API:"
            )

            print(
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
# WHALE MESSAGE
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


    if isinstance(
        sender,
        dict
    ):

        sender_owner = (
            sender.get(
                "owner"
            )
            or
            "نهنگ ناشناس"
        )

    else:

        sender_owner = (
            "نهنگ ناشناس"
        )


    if isinstance(
        receiver,
        dict
    ):

        receiver_owner = (
            receiver.get(
                "owner"
            )
            or
            "نهنگ ناشناس"
        )

    else:

        receiver_owner = (
            "نهنگ ناشناس"
        )


    if amount_usd >= WHALE_L2_USD:

        level = (
            "🔴 سطح ۲ | "
            "حرکت بسیار سنگین"
        )

    else:

        level = (
            "🟡 سطح ۱ | "
            "حرکت سنگین"
        )


    if (

        sender_owner != "نهنگ ناشناس"

        and

        receiver_owner ==
        "نهنگ ناشناس"

    ):

        interpretation = (

            "دارایی از یک موجودیت "
            "شناخته‌شده به یک مقصد "
            "ناشناخته منتقل شده است."

        )


    elif (

        sender_owner ==
        "نهنگ ناشناس"

        and

        receiver_owner !=
        "نهنگ ناشناس"

    ):

        interpretation = (

            "دارایی به یک موجودیت "
            "شناخته‌شده منتقل شده است."

        )


    else:

        interpretation = (

            "یک انتقال بسیار بزرگ "
            "شناسایی شده است. "
            "جهت خرید یا فروش از "
            "این تراکنش به‌تنهایی "
            "قابل تعیین نیست."

        )


    return f"""
━━━━━━━━━━━━━━━━━━━━
🐋 WHALE ALERT
{level}
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
🧠 تحلیل رادار
━━━━━━━━━━━━━━━━━━━━

{interpretation}

⚠️ انتقال بزرگ به‌تنهایی
به معنی خرید یا فروش قطعی
نیست.

━━━━━━━━━━━━━━━━━━━━
🔗 Transaction

{tx_hash}

━━━━━━━━━━━━━━━━━━━━
"""


# ============================================================
# MAIN
# ============================================================

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


    print(
        "Telegram personal target:",
        CHAT_ID
    )


    if CHANNEL_ID:

        print(
            "Telegram channel target:",
            clean_telegram_target(
                CHANNEL_ID
            )
        )

    else:

        print(
            "Telegram channel target: "
            "NOT CONFIGURED"
        )


    if HF_TOKEN:

        print(
            "AI: ENABLED"
        )

    else:

        print(
            "AI: FALLBACK MODE"
        )


    if WHALE_ALERT_API_KEY:

        print(
            "Whale Alert API: ENABLED"
        )

    else:

        print(
            "Whale Alert API: DISABLED"
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
                feed.get(
                    "name",
                    "Unknown"
                ),
                "|",
                error
            )

            continue


        total_articles += len(
            articles
        )


        for article in articles:

            identifier = make_id(

                article["link"]

                or

                article["title"]

            )


            if identifier in state[
                "seen"
            ]:

                continue


            state[
                "seen"
            ].append(
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

                message = (
                    build_news_message(
                        article,
                        score,
                        analysis
                    )
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

            "WHALE|"
            + tx_hash

        )


        if identifier in state[
            "seen"
        ]:

            continue


        state[
            "seen"
        ].append(
            identifier
        )


        message = (
            format_whale_alert(
                tx
            )
        )


        broadcast(
            message
        )


        whale_alerts += 1


        if whale_alerts >= (
            WHALE_MAX_PER_RUN
        ):

            break


    # ========================================================
    # SAVE STATE
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


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
