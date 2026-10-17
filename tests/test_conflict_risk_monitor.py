import unittest

from src.conflict_risk_monitor import compose_assessment, build_alert


class ConflictRiskMonitorTests(unittest.TestCase):
    def test_alert_requires_high_score_and_independent_signal_families(self):
        news = {"score": 45, "high_severity_count": 3, "domains": ["a.example", "b.example"]}
        shipping = {"score": 20}
        flights = {"score": 8}
        result = compose_assessment(news, shipping, flights)
        self.assertEqual(result["score"], 73)
        self.assertTrue(result["alert_eligible"])
        self.assertGreaterEqual(len(result["elevated_domains"]), 2)

    def test_high_news_score_without_corroboration_does_not_alert(self):
        news = {"score": 45, "high_severity_count": 3, "domains": ["one.example"]}
        shipping = {"score": 0}
        flights = {"score": 0}
        result = compose_assessment(news, shipping, flights)
        self.assertFalse(result["alert_eligible"])

    def test_alert_message_disclaims_probability(self):
        message = build_alert(
            {"article_count": 3, "high_severity_count": 2, "headlines": []},
            {"score": 20, "decline_fraction": 0.55},
            {"score": 8, "deviation_fraction": 0.7},
            {"score": 73, "elevated_domains": ["news", "shipping", "aviation"], "alert_eligible": True},
        )
        self.assertIn("شاخص ریسک تحلیلی: 73/100", message)
        self.assertIn("به معنی احتمال وقوع 73٪ نیست", message)


if __name__ == "__main__":
    unittest.main()
