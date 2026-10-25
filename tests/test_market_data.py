import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# main.py validates these at import time; tests never send Telegram messages.
os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
os.environ["TELEGRAM_CHAT_ID"] = "test-chat"
os.environ["TELEGRAM_CHANNEL_ID"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import main as radar


class MarketDataRegressionTests(unittest.TestCase):
    def test_tgju_skips_small_numbers_and_finds_real_price(self):
        page = (
            "<div>نرخ فعلی:</div><span>2</span>"
            "<span>258,791,000</span><span>1.12</span>"
        )
        self.assertEqual(
            radar.extract_tgju_current_price(page, min_price=1_000_000),
            258791000.0,
        )

    def test_tgju_rejects_unrealistic_price(self):
        page = "<div>نرخ فعلی: 2</div><span>1.12%</span>"
        self.assertEqual(
            radar.extract_tgju_current_price(page, min_price=1_000_000),
            0.0,
        )

    def test_whale_fallback_translates_common_transfer_format(self):
        source = (
            "124,600,000 USDT (124,525,240 USD) transferred "
            "from #Bitfinex to Tether Treasury Details"
        )
        result = radar.fallback_translate_whale(source)
        self.assertIn("124,600,000 USDT", result)
        self.assertIn("124,525,240 دلار آمریکا", result)
        self.assertIn("Bitfinex", result)
        self.assertIn("Tether Treasury", result)
        self.assertIn("خرید یا فروش", result)

    def test_snapshot_does_not_publish_zero_price_as_real_data(self):
        with patch.object(
            radar,
            "fetch_tgju_market",
            return_value={"usd": {}, "gold": {}},
        ), patch.object(
            radar,
            "fetch_crypto_market",
            return_value={
                "btc": {"usd": 80492, "change": 0.07},
                "eth": {"usd": 2348, "change": 0.46},
            },
        ):
            message = radar.build_market_snapshot()

        self.assertIn("داده ناموجود", message)
        self.assertIn("تغییر ناموجود", message)
        self.assertNotIn("0 تومان", message)
        self.assertIn("زمان تهیه گزارش", message)


if __name__ == "__main__":
    unittest.main()
