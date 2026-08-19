import os
import json
import re
import html
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


# ============================================================
# AI MARKET RADAR
# NEWS + AI + WHALE CHANNEL + WHALE ALERT API
# TGJU USD + GOLD
# TELEGRAM BROADCAST
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
    "@HuntFlo"
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

COINGECKO_API_KEY = os.getenv(
    "COINGECKO_API_KEY",
    ""
).strip()

MARKET_SNAPSHOT_ENABLED = os.getenv(
    "MARKET_SNAPSHOT_ENABLED",
    "true"
).strip().lower() == "true"


# ============================================================
# CONSTANTS
# ============================================================

MY_CHANNEL = "@HuntFlo"
MY_BOT = "@notash_news_bot"

SOURCE_WHALE_CHANNEL = "@whale_alert_io"

TGJU_BASE_URL = "https://www.tgju.org"

TGJU_PROFILES = {
    "usd": "/profile/price_dollar_rl",
    "gold18": "/profile/tgju_gold_irg18"
}

MARKET_UPDATE_HOURS = 5

TELEGRAM_MAX_LENGTH = 3900

WHALE_CHANNEL_MAX_MESSAGES = 5


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
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
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
# TELEGRAM MESSAGE SPLITTER
# ============================================================

def split_telegram_message(
    message,
    max_length=TELEGRAM_MAX_LENGTH
):

    if not message:
        return []

    if len(message) <= max_length:
        return [message]

    parts = []

    remaining = message

    while len(remaining) > max_length:

        cut = remaining.rfind(
            "\n",
            0,
            max_length
        )

        if cut < 1000:

            cut = remaining.rfind(
                " ",
                0,
                max_length
            )

        if cut < 1000:

            cut = max_length

        parts.append(
            remaining[:cut].strip()
        )

        remaining = (
            remaining[cut:]
            .strip()
        )

    if remaining:
        parts.append(
            remaining
        )

    return parts


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
        "chat_id": target,
        "text": message,
        "disable_web_page_preview": "true"
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type":
            "application/x-www-form-urlencoded; "
            "charset=UTF-8",

            "User-Agent":
            "AI-Market-Radar/3.0"
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

    if not result.get("ok"):

        raise RuntimeError(
            f"{target_name}: Telegram API "
            f"rejected message: {result}"
        )

    return result


# ============================================================
# BROADCAST
# ============================================================

def broadcast(message):

    print("")
    print("================================")
    print("TELEGRAM BROADCAST")
    print("================================")

    parts = split_telegram_message(
        message
    )

    # --------------------------------------------------------
    # PERSONAL
    # --------------------------------------------------------

    try:

        for index, part in enumerate(
            parts,
            start=1
        ):

            result = send_telegram(
                part,
                CHAT_ID,
                "Personal Chat"
            )

            message_id = (
                result
                .get("result", {})
                .get(
                    "message_id",
                    "unknown"
                )
            )

            print(
                f"PERSONAL CHAT: OK "
                f"{index}/{len(parts)} "
                f"| message_id={message_id}"
            )

    except Exception as error:

        print(
            "PERSONAL CHAT ERROR:"
        )

        print(error)

    # --------------------------------------------------------
    # CHANNEL
    # --------------------------------------------------------

    if not CHANNEL_ID:

        print(
            "CHANNEL: NOT CONFIGURED"
        )

        return

    channel_target = clean_telegram_target(
        CHANNEL_ID
    )

    try:

        for index, part in enumerate(
            parts,
            start=1
        ):

            result = send_telegram(
                part,
                channel_target,
                "Channel"
            )

            message_id = (
                result
                .get("result", {})
                .get(
                    "message_id",
                    "unknown"
                )
            )

            print(
                f"CHANNEL: OK "
                f"{index}/{len(parts)} "
                f"| message_id={message_id}"
            )

    except Exception as error:

        print(
            "CHANNEL ERROR:"
        )

        print(error)

        print(
            "اگر خطای 403 دریافت شد، "
            "ربات باید عضو کانال باشد."
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
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36",

            "Accept":
            "text/html, "
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
# JSON FETCH
# ============================================================

def get_json(
    url,
    headers=None
):

    request_headers = {

        "User-Agent":
        "AI-Market-Radar/3.0",

        "Accept":
        "application/json"
    }

    if headers:

        request_headers.update(
            headers
        )

    request = urllib.request.Request(
        url,
        headers=request_headers
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        raw = (
            response
            .read()
            .decode(
                "utf-8",
                errors="replace"
            )
        )

        return json.loads(
            raw
        )


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

        if "whale_channel_seen" not in state:
            state["whale_channel_seen"] = []

        return state

    except Exception:

        return {

            "seen": [],

            "whale_channel_seen": [],

            "last_market_snapshot": ""
        }


def save_state(state):

    state["seen"] = (
        state.get(
            "seen",
            []
        )
    )[-5000:]

    state["whale_channel_seen"] = (
        state.get(
            "whale_channel_seen",
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
# HASH
# ============================================================

def make_id(text):

    return hashlib.sha256(
        text.encode("utf-8")
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
# AI CLIENT
# ============================================================

def get_ai_client():

    if not HF_TOKEN:
        return None

    if InferenceClient is None:
        return None

    try:

        return InferenceClient(
            provider="auto",
            api_key=HF_TOKEN
        )

    except Exception as error:

        print(
            "AI CLIENT ERROR:",
            error
        )

        return None


# ============================================================
# NEWS AI ANALYSIS
# ============================================================

def ai_analyze_news(
    article,
    score
):

    client = get_ai_client()

    if client is None:

        print(
            "AI unavailable - "
            "fallback mode"
        )

        return None

    prompt = f"""
تو یک تحلیلگر ارشد بازارهای مالی،
فارکس و کریپتو هستی.

خبر:

عنوان:
{article["title"]}

متن:
{article["description"]}

امتیاز اولیه اهمیت:
{score}/10

تحلیل را به فارسی ارائه کن.

مهم:
تحلیل را حذف یا بیش از حد کوتاه نکن.
اما از مقدمه و تکرار غیرضروری خودداری کن.

ساختار:

📌 خلاصه
خلاصه دقیق خبر در 2 تا 4 جمله.

🎯 چرا مهم است؟
مهم‌ترین دلیل تأثیرگذاری خبر.

📈 کریپتو
اثر احتمالی روی BTC و ETH.

💵 دلار / فارکس
اثر احتمالی روی دلار و بازار ارز.

🥇 طلا
اثر احتمالی روی طلا.

🛢 نفت
در صورت ارتباط با خبر، اثر احتمالی نفت.

📊 سهام
در صورت ارتباط، اثر احتمالی بازار سهام.

🧭 جهت احتمالی
مثبت / منفی / خنثی + دلیل.

⏱ بازه اثر
کوتاه‌مدت / میان‌مدت / بلندمدت.

🎯 اطمینان
درصد تقریبی اطمینان تحلیل.

⚠️ ریسک
مهم‌ترین چیزی که می‌تواند تحلیل را تغییر دهد.

سیگنال خرید یا فروش قطعی صادر نکن.
هیچ پیش‌بینی‌ای را قطعی معرفی نکن.
"""

    try:

        response = client.chat_completion(

            model=AI_MODEL,

            messages=[

                {
                    "role":
                    "system",

                    "content":
                    "تو یک تحلیلگر حرفه‌ای "
                    "بازارهای مالی هستی. "
                    "فارسی روان و دقیق بنویس."
                },

                {
                    "role":
                    "user",

                    "content":
                    prompt
                }
            ],

            temperature=0.1,

            max_tokens=1400
        )

        return (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

    except Exception as error:

        print(
            "AI NEWS ERROR:",
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

    if not analysis:

        analysis = (
            "تحلیل AI در این اجرا "
            "در دسترس نبود."
        )

    footer = f"""
━━━━━━━━━━━━━━━━━━━━
📡 {MY_CHANNEL}
🤖 {MY_BOT}
"""

    return f"""
🤖 AI MARKET RADAR | {level}

📰 {article["title"]}

📊 اهمیت: {score}/10

━━━━━━━━━━━━━━━━━━━━
🧠 تحلیل AI
━━━━━━━━━━━━━━━━━━━━

{analysis}

━━━━━━━━━━━━━━━━━━━━
📰 منبع: {article["source"]}

🔗 {article["link"]}

⚠️ تحلیل احتمالی است و سیگنال قطعی
خرید یا فروش محسوب نمی‌شود.
{footer}
""".strip()


# ============================================================
# PUBLIC TELEGRAM CHANNEL
# WHALE ALERT SOURCE
# ============================================================

def fetch_public_channel_messages():

    channel_username = (
        SOURCE_WHALE_CHANNEL
        .replace("@", "")
        .strip()
    )

    url = (
        "https://t.me/s/"
        + channel_username
    )

    print(
        "FETCHING PUBLIC TELEGRAM CHANNEL:",
        SOURCE_WHALE_CHANNEL
    )

    try:

        raw = fetch_url(
            url
        )

        page = raw.decode(
            "utf-8",
            errors="replace"
        )

    except Exception as error:

        print(
            "PUBLIC CHANNEL ERROR:",
            error
        )

        return []

    messages = []

    # --------------------------------------------------------
    # Message blocks
    # --------------------------------------------------------

    blocks = re.findall(
        r'<div class="tgme_widget_message_wrap.*?'
        r'</div>\s*</div>',
        page,
        flags=re.DOTALL
    )

    for block in blocks:

        # message id
        message_match = re.search(
            r'data-post="'
            + re.escape(channel_username)
            + r'/(\d+)"',
            block
        )

        if not message_match:
            continue

        message_id = (
            message_match.group(1)
        )

        # message text
        text_match = re.search(
            r'<div class="tgme_widget_message_text[^>]*>'
            r'(.*?)'
            r'</div>',
            block,
            flags=re.DOTALL
        )

        if text_match:

            text = clean_text(
                text_match.group(1)
            )

        else:

            text = ""

        # message link
        link = (
            f"https://t.me/"
            f"{channel_username}/"
            f"{message_id}"
        )

        if not text:
            continue

        messages.append({

            "id":
            message_id,

            "text":
            text,

            "link":
            link,

            "source":
            SOURCE_WHALE_CHANNEL
        })

    # newest first
    messages.reverse()

    return messages[
        :WHALE_CHANNEL_MAX_MESSAGES
    ]


# ============================================================
# AI WHALE CHANNEL
# TRANSLATION + ANALYSIS
# ============================================================

def ai_analyze_whale_channel(
    original_text
):

    client = get_ai_client()

    if client is None:

        print(
            "AI unavailable for "
            "Whale channel"
        )

        return None

    prompt = f"""
پیام زیر دقیقاً از کانال عمومی
Whale Alert دریافت شده است.

پیام اصلی:

----------------
{original_text}
----------------

وظیفه:

1. ابتدا پیام را به فارسی ترجمه کن.
ترجمه باید وفادار به متن اصلی باشد.
اطلاعات، عددها، نام‌ها، آدرس‌ها و مقادیر
را تغییر نده.

2. سپس پیام را تحلیل کن.

3. اگر پیام فقط یک انتقال بلاکچینی است،
از روی آن خرید یا فروش قطعی نتیجه نگیر.

4. اگر نام صرافی، شرکت، نهنگ یا مالک
مشخص شده، همان نام را حفظ کن.

ساختار خروجی دقیقاً:

🇮🇷 ترجمه دقیق

[ترجمه فارسی]

━━━━━━━━━━━━━━━━━━━━

🐋 تحلیل Whale Radar

💰 دارایی و ارزش:
...

👤 مبدأ:
...

👤 مقصد:
...

🏦 نوع مقصد:
صرافی / کیف پول / نامشخص

🧭 برداشت احتمالی بازار:
مثبت / منفی / خنثی / نامشخص

📈 اثر احتمالی روی بازار:
...

⏱ بازه اثر:
کوتاه‌مدت / میان‌مدت / نامشخص

🎯 اطمینان:
...%

⚠️ نکته:
...

تحلیل را کامل انجام بده ولی از
مقدمه‌گویی و تکرار جلوگیری کن.
"""

    try:

        response = client.chat_completion(

            model=AI_MODEL,

            messages=[

                {
                    "role":
                    "system",

                    "content":
                    "تو تحلیلگر حرفه‌ای "
                    "تراکنش‌های بزرگ کریپتو "
                    "و مترجم دقیق انگلیسی به فارسی هستی."
                },

                {
                    "role":
                    "user",

                    "content":
                    prompt
                }
            ],

            temperature=0.1,

            max_tokens=1500
        )

        return (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

    except Exception as error:

        print(
            "AI WHALE CHANNEL ERROR:",
            error
        )

        return None


# ============================================================
# WHALE CHANNEL MESSAGE
# ============================================================

def build_whale_channel_message(
    item,
    analysis
):

    if not analysis:

        analysis = (
            "ترجمه و تحلیل AI "
            "در دسترس نبود.\n\n"
            + item["text"]
        )

    return f"""
🐋 WHALE ALERT RADAR

{analysis}

━━━━━━━━━━━━━━━━━━━━
📡 منبع اصلی:
{SOURCE_WHALE_CHANNEL}

🔗 {item["link"]}

⚠️ انتقال بزرگ به‌تنهایی به معنی
خرید یا فروش قطعی نیست.

━━━━━━━━━━━━━━━━━━━━
📡 {MY_CHANNEL}
🤖 {MY_BOT}
""".strip()


# ============================================================
# PROCESS WHALE CHANNEL
# ============================================================

def process_whale_channel(
    state
):

    messages = (
        fetch_public_channel_messages()
    )

    if not messages:

        print(
            "No public Whale Alert messages found."
        )

        return 0

    sent = 0

    for item in messages:

        identifier = make_id(
            "PUBLIC_WHALE|"
            + item["id"]
        )

        if identifier in state[
            "whale_channel_seen"
        ]:

            continue

        print(
            "NEW WHALE CHANNEL MESSAGE:",
            item["id"]
        )

        analysis = (
            ai_analyze_whale_channel(
                item["text"]
            )
        )

        message = (
            build_whale_channel_message(
                item,
                analysis
            )
        )

        broadcast(
            message
        )

        state[
            "whale_channel_seen"
        ].append(
            identifier
        )

        sent += 1

    return sent


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
            raw.decode(
                "utf-8"
            )
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
# SAFE FLOAT
# ============================================================

def safe_float(
    value,
    default=0.0
):

    try:

        if value is None:
            return default

        if isinstance(
            value,
            str
        ):

            value = (
                value
                .replace(",", "")
                .replace("٬", "")
                .strip()
            )

        return float(
            value
        )

    except Exception:

        return default


# ============================================================
# NORMALIZE DIGITS
# ============================================================

def normalize_digits(text):

    if text is None:
        return ""

    translation_table = str.maketrans(

        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",

        "01234567890123456789"
    )

    return str(
        text
    ).translate(
        translation_table
    )


# ============================================================
# MARKET NUMBER
# ============================================================

def parse_market_number(
    value
):

    if value is None:
        return 0.0

    value = normalize_digits(
        value
    )

    value = (
        value
        .replace(",", "")
        .replace("٬", "")
        .replace("٫", ".")
        .replace("ریال", "")
        .replace("تومان", "")
        .strip()
    )

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value
    )

    if not match:
        return 0.0

    try:

        return float(
            match.group(0)
        )

    except Exception:

        return 0.0


# ============================================================
# TGJU FETCH
# ============================================================

def fetch_tgju_page(
    profile_path
):

    url = (
        TGJU_BASE_URL
        + profile_path
    )

    request = urllib.request.Request(

        url,

        headers={

            "User-Agent":
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36",

            "Accept":
            "text/html,"
            "application/xhtml+xml,"
            "application/xml;q=0.9,"
            "*/*;q=0.8",

            "Accept-Language":
            "fa-IR,fa;q=0.9,en;q=0.8",

            "Cache-Control":
            "no-cache"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return response.read().decode(
            "utf-8",
            errors="replace"
        )


# ============================================================
# TGJU PRICE EXTRACTION
# ============================================================

def extract_tgju_current_price(
    html_content
):

    if not html_content:
        return 0.0

    normalized = normalize_digits(
        html_content
    )

    patterns = [

        r"نرخ\s*فعلی.{0,500}?"
        r"(\d[\d,٬\.]*)",

        r"نرخ\s*فعلی\s*[:：]\s*"
        r"(\d[\d,٬\.]*)",

        r'"price"\s*:\s*"?'
        r"(\d[\d,٬\.]*)",

        r'"value"\s*:\s*"?'
        r"(\d[\d,٬\.]*)",

        r'"last"\s*:\s*"?'
        r"(\d[\d,٬\.]*)",

        r'"current"\s*:\s*"?'
        r"(\d[\d,٬\.]*)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized,
            flags=
            re.IGNORECASE |
            re.DOTALL
        )

        if match:

            value = parse_market_number(
                match.group(1)
            )

            if value > 0:

                return value

    return 0.0


# ============================================================
# TGJU CHANGE
# ============================================================

def extract_tgju_change(
    html_content
):

    if not html_content:
        return 0.0

    normalized = normalize_digits(
        html_content
    )

    patterns = [

        r"درصد\s*تغییر"
        r".{0,500}?"
        r"(-?\d+(?:\.\d+)?)\s*%",

        r"Change\s*%"
        r".{0,300}?"
        r"(-?\d+(?:\.\d+)?)\s*%"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized,
            flags=
            re.IGNORECASE |
            re.DOTALL
        )

        if match:

            return parse_market_number(
                match.group(1)
            )

    return 0.0


# ============================================================
# TGJU ITEM
# ============================================================

def fetch_tgju_item(
    name,
    profile_path
):

    print(
        f"TGJU: fetching {name}..."
    )

    try:

        page = fetch_tgju_page(
            profile_path
        )

        price = (
            extract_tgju_current_price(
                page
            )
        )

        change = (
            extract_tgju_change(
                page
            )
        )

        if price <= 0:

            print(
                f"TGJU {name}: "
                "price not found"
            )

            return {}

        # TGJU داخلی معمولاً ریال است
        toman_price = (
            price / 10
        )

        print(
            f"TGJU {name}: "
            f"{toman_price:,.0f} تومان"
        )

        return {

            "price":
            toman_price,

            "raw_price":
            price,

            "change":
            change,

            "source":
            "TGJU",

            "url":
            TGJU_BASE_URL
            + profile_path
        }

    except Exception as error:

        print(
            f"TGJU {name} ERROR:",
            error
        )

        return {}


# ============================================================
# USD + GOLD FROM TGJU
# ============================================================

def fetch_tgju_market():

    print(
        "================================"
    )

    print(
        "FETCHING TGJU MARKET"
    )

    print(
        "USD + GOLD 18"
    )

    print(
        "================================"
    )

    usd = fetch_tgju_item(

        "USD FREE MARKET",

        TGJU_PROFILES[
            "usd"
        ]
    )

    gold = fetch_tgju_item(

        "GOLD 18",

        TGJU_PROFILES[
            "gold18"
        ]
    )

    return {

        "usd":
        usd,

        "gold":
        gold
    }


# ============================================================
# CRYPTO
# ============================================================

def fetch_crypto_market():

    url = (
        "https://api.coingecko.com/api/v3/"
        "simple/price"
        "?ids=bitcoin,ethereum"
        "&vs_currencies=usd"
        "&include_24hr_change=true"
    )

    headers = {

        "User-Agent":
        "AI-Market-Radar/3.0",

        "Accept":
        "application/json"
    }

    if COINGECKO_API_KEY:

        headers[
            "x-cg-demo-api-key"
        ] = COINGECKO_API_KEY

    try:

        data = get_json(
            url,
            headers
        )

        bitcoin = data.get(
            "bitcoin",
            {}
        )

        ethereum = data.get(
            "ethereum",
            {}
        )

        return {

            "btc": {

                "usd":
                safe_float(
                    bitcoin.get(
                        "usd"
                    )
                ),

                "change":
                safe_float(
                    bitcoin.get(
                        "usd_24h_change"
                    )
                )
            },

            "eth": {

                "usd":
                safe_float(
                    ethereum.get(
                        "usd"
                    )
                ),

                "change":
                safe_float(
                    ethereum.get(
                        "usd_24h_change"
                    )
                )
            }
        }

    except Exception as error:

        print(
            "CRYPTO MARKET ERROR:",
            error
        )

        return {}


# ============================================================
# CHANGE FORMAT
# ============================================================

def format_change(
    value
):

    value = safe_float(
        value
    )

    if value > 0:

        return (
            f"🟢 +{value:.2f}%"
        )

    if value < 0:

        return (
            f"🔴 {value:.2f}%"
        )

    return (
        "⚪ 0.00%"
    )


# ============================================================
# MARKET SNAPSHOT
# COMPACT BUT USEFUL
# ============================================================

def build_market_snapshot():

    market = fetch_tgju_market()

    crypto = fetch_crypto_market()

    usd = market.get(
        "usd",
        {}
    )

    gold = market.get(
        "gold",
        {}
    )

    btc = crypto.get(
        "btc",
        {}
    )

    eth = crypto.get(
        "eth",
        {}
    )

    usd_toman = safe_float(
        usd.get(
            "price"
        )
    )

    gold_toman = safe_float(
        gold.get(
            "price"
        )
    )

    btc_usd = safe_float(
        btc.get(
            "usd"
        )
    )

    eth_usd = safe_float(
        eth.get(
            "usd"
        )
    )

    btc_toman = (
        btc_usd
        * usd_toman
    )

    eth_toman = (
        eth_usd
        * usd_toman
    )

    now = datetime.now(
        timezone.utc
    )

    update_time = now.strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    usd_display = (
        f"{usd_toman:,.0f} تومان"
        if usd_toman > 0
        else
        "داده ناموجود"
    )

    gold_display = (
        f"{gold_toman:,.0f} تومان"
        if gold_toman > 0
        else
        "داده ناموجود"
    )

    btc_display = (
        f"${btc_usd:,.0f}"
        if btc_usd > 0
        else
        "ناموجود"
    )

    eth_display = (
        f"${eth_usd:,.0f}"
        if eth_usd > 0
        else
        "ناموجود"
    )

    return f"""
📊 MARKET SNAPSHOT

💵 دلار آزاد:
{usd_display}
{format_change(usd.get("change", 0))}

🥇 طلای ۱۸ عیار:
{gold_display}
{format_change(gold.get("change", 0))}

₿ BTC:
{btc_display}
{format_change(btc.get("change", 0))}

♦️ ETH:
{eth_display}
{format_change(eth.get("change", 0))}

💡 ارزش تقریبی BTC:
{btc_toman:,.0f} تومان

━━━━━━━━━━━━━━━━━━━━
🕐 بروزرسانی: هر ۵ ساعت
📡 منبع دلار و طلا: TGJU
📡 کریپتو: CoinGecko

⚠️ قیمت‌ها لحظه‌ای هستند و بین
دو بروزرسانی ممکن است تغییر کنند.

━━━━━━━━━━━━━━━━━━━━
📡 {MY_CHANNEL}
🤖 {MY_BOT}
""".strip()


# ============================================================
# MARKET SNAPSHOT TIMER
# ============================================================

def should_send_market_snapshot(
    state
):

    last_time = state.get(
        "last_market_snapshot",
        ""
    )

    if not last_time:

        return True

    try:

        last = datetime.fromisoformat(
            last_time
        )

        now = datetime.now(
            timezone.utc
        )

        elapsed = (
            now - last
        ).total_seconds()

        return (
            elapsed
            >=
            MARKET_UPDATE_HOURS
            * 3600
        )

    except Exception:

        return True


# ============================================================
# SEND MARKET SNAPSHOT
# ============================================================

def send_market_snapshot(
    state
):

    if not MARKET_SNAPSHOT_ENABLED:

        print(
            "Market Snapshot: DISABLED"
        )

        return False

    if not should_send_market_snapshot(
        state
    ):

        print(
            "Market Snapshot: "
            "not due yet"
        )

        return False

    print(
        "================================"
    )

    print(
        "SENDING MARKET SNAPSHOT"
    )

    print(
        "================================"
    )

    try:

        message = (
            build_market_snapshot()
        )

        broadcast(
            message
        )

        state[
            "last_market_snapshot"
        ] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        print(
            "MARKET SNAPSHOT: OK"
        )

        return True

    except Exception as error:

        print(
            "MARKET SNAPSHOT ERROR:",
            error
        )

        return False


# ============================================================
# WHALE ALERT MESSAGE
# COMPACT PERSIAN FORMAT
# ============================================================

def format_whale_alert(tx):

    amount = safe_float(
        tx.get(
            "amount",
            0
        )
    )

    amount_usd = safe_float(
        tx.get(
            "amount_usd",
            0
        )
    )

    symbol = (
        tx.get(
            "symbol",
            "UNKNOWN"
        )
        or
        "UNKNOWN"
    )

    blockchain = (
        tx.get(
            "blockchain",
            "Unknown"
        )
        or
        "Unknown"
    )

    sender = tx.get(
        "from",
        {}
    )

    receiver = tx.get(
        "to",
        {}
    )

    # --------------------------------------------------------
    # SENDER
    # --------------------------------------------------------

    if isinstance(
        sender,
        dict
    ):

        sender_owner = (
            sender.get(
                "owner"
            )
            or
            "نهنگ ناشناخته"
        )

    else:

        sender_owner = (
            "نهنگ ناشناخته"
        )

    # --------------------------------------------------------
    # RECEIVER
    # --------------------------------------------------------

    if isinstance(
        receiver,
        dict
    ):

        receiver_owner = (
            receiver.get(
                "owner"
            )
            or
            "نهنگ ناشناخته"
        )

    else:

        receiver_owner = (
            "نهنگ ناشناخته"
        )

    # --------------------------------------------------------
    # WHALE LEVEL
    # --------------------------------------------------------

    if amount_usd >= WHALE_L2_USD:

        level = (
            "🔴 سطح ۲ | حرکت بسیار سنگین"
        )

    else:

        level = (
            "🟡 سطح ۱ | حرکت سنگین"
        )

    # --------------------------------------------------------
    # MARKET INTERPRETATION
    # --------------------------------------------------------

    if (
        sender_owner != "نهنگ ناشناخته"
        and
        receiver_owner == "نهنگ ناشناخته"
    ):

        interpretation = (
            "دارایی از یک موجودیت شناخته‌شده "
            "به یک مقصد ناشناخته منتقل شده است."
        )

        market_direction = "خنثی"

        market_effect = (
            "اثر قابل توجهی قابل تأیید نیست"
        )

    elif (
        sender_owner == "نهنگ ناشناخته"
        and
        receiver_owner != "نهنگ ناشناخته"
    ):

        interpretation = (
            "دارایی به یک موجودیت شناخته‌شده "
            "منتقل شده است."
        )

        market_direction = "خنثی"

        market_effect = (
            "اثر قابل توجهی قابل تأیید نیست"
        )

    else:

        interpretation = (
            "یک انتقال بسیار بزرگ شناسایی شده است. "
            "از این تراکنش به‌تنهایی نمی‌توان خرید "
            "یا فروش قطعی را نتیجه گرفت."
        )

        market_direction = "خنثی"

        market_effect = (
            "هیچ تأثیر قابل توجهی قابل تأیید نیست"
        )

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    if amount_usd >= WHALE_L2_USD:

        confidence = 75

    elif amount_usd >= WHALE_MIN_USD:

        confidence = 60

    else:

        confidence = 50

    # --------------------------------------------------------
    # COMPACT MESSAGE
    # --------------------------------------------------------

    return f"""
🐋 WHALE ALERT RADAR
🇮🇷 ترجمه دقیق

━━━━━━━━━━━━━━━━━━━━
🚨 🚨 🚨 🚨 🚨 🚨 🚨 🚨
{amount_usd:,.0f} دلار {symbol}
از {sender_owner} به {receiver_owner} انتقال یافت

━━━━━━━━━━━━━━━━━━━━
🐋 تحلیل Whale Radar

💰 دارایی و ارزش:
{amount:,.4f} {symbol} ({amount_usd:,.0f} USD)

👤 مبدأ: {sender_owner}
👤 مقصد: {receiver_owner}
🏦 نوع مقصد: {blockchain}

🧭 برداشت احتمالی بازار: {market_direction}
📈 اثر احتمالی روی بازار: {market_effect}
⏱ بازه اثر: کوتاه‌مدت
🎯 اطمینان: {confidence}%

⚠️ نکته:
{interpretation}

━━━━━━━━━━━━━━━━━━━━
⚠️ انتقال بزرگ به‌تنهایی به معنی
خرید یا فروش قطعی نیست.

━━━━━━━━━━━━━━━━━━━━
📡 @HuntFlo
🤖 @notash_news_bot
""".strip()

# ============================================================
# WELCOME MESSAGE
# ============================================================

WELCOME_TEST_MESSAGE = f"""
🤖 AI MARKET RADAR

سیستم رادار هوشمند بازار فعال شد.

📰 پایش اخبار مالی
🐋 رهگیری تراکنش‌های بزرگ
🧠 تحلیل هوش مصنوعی
💵 پایش دلار و طلا
📊 پایش BTC و ETH

هدف سیستم:
شناسایی سریع خبرها و حرکات مهمی
که می‌توانند روی بازار اثر بگذارند.

⚠️ اطلاعات و تحلیل‌ها احتمالی هستند
و جایگزین مدیریت ریسک و تصمیم شخصی
معامله‌گر نیستند.

━━━━━━━━━━━━━━━━━━━━
📡 کانال:
{MY_CHANNEL}

🤖 ربات:
{MY_BOT}
""".strip()


def send_welcome_test_once(
    state
):

    if state.get(
        "welcome_test_sent",
        False
    ):

        return False

    if not CHANNEL_ID:

        return False

    print(
        "SENDING WELCOME TEST"
    )

    try:

        send_telegram(
            WELCOME_TEST_MESSAGE,
            CHANNEL_ID,
            "Welcome Test"
        )

        state[
            "welcome_test_sent"
        ] = True

        print(
            "WELCOME TEST: OK"
        )

        return True

    except Exception as error:

        print(
            "WELCOME TEST ERROR:",
            error
        )

        return False


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

    print(
        "Telegram channel target:",
        clean_telegram_target(
            CHANNEL_ID
        )
    )

    print(
        "Source Whale Channel:",
        SOURCE_WHALE_CHANNEL
    )

    print(
        "My Channel:",
        MY_CHANNEL
    )

    print(
        "My Bot:",
        MY_BOT
    )

    print(
        "Market update:",
        f"every {MARKET_UPDATE_HOURS} hours"
    )

    print(
        "AI:",
        "ENABLED"
        if HF_TOKEN
        else
        "FALLBACK"
    )

    print(
        "Whale API:",
        "ENABLED"
        if WHALE_ALERT_API_KEY
        else
        "DISABLED"
    )

    print(
        "================================"
    )

    state = load_state()

    # ========================================================
    # WELCOME
    # ========================================================

    send_welcome_test_once(
        state
    )

    total_articles = 0
    new_articles = 0
    news_alerts = 0
    whale_alerts = 0
    whale_channel_alerts = 0

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

            min_score = float(
                CONFIG.get(
                    "news_min_score",
                    3.5
                )
            )

            alert_score = float(
                CONFIG.get(
                    "alert_min_score",
                    5.5
                )
            )

            if score < min_score:
                continue

            analysis = (
                ai_analyze_news(
                    article,
                    score
                )
            )

            if score >= alert_score:

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

                max_alerts = int(
                    CONFIG.get(
                        "max_alerts_per_run",
                        8
                    )
                )

                if (
                    news_alerts
                    >=
                    max_alerts
                ):

                    break

    # ========================================================
    # PUBLIC WHALE ALERT CHANNEL
    # ========================================================

    try:

        whale_channel_alerts = (
            process_whale_channel(
                state
            )
        )

    except Exception as error:

        print(
            "WHALE CHANNEL PROCESS ERROR:",
            error
        )

    # ========================================================
    # WHALE ALERT API
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
    # MARKET SNAPSHOT
    # ONLY EVERY 5 HOURS
    # ========================================================

    send_market_snapshot(
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
        "PUBLIC WHALE ALERTS:",
        whale_channel_alerts
    )

    print(
        "WHALE API ALERTS:",
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
