import unittest
from unittest import mock

from integrations import weather
from integrations.gateway import GatewayError


class WeatherTest(unittest.TestCase):
    @mock.patch("integrations.legacy_http.fetch")
    def test_returns_forecast(self, fetch):
        result = {"city": "Bergen", "days": [{"date": "2031-04-02", "high": 9.0, "low": 4.5, "summary": "rain"}]}
        fetch.return_value = {"ok": True, "result": result}
        self.assertEqual(weather.get_forecast("Bergen"), result)
        self.assertIn("/weather?city=Bergen", fetch.call_args.args[0])

    @mock.patch("integrations.legacy_http.fetch")
    def test_unknown_city(self, fetch):
        fetch.return_value = {"ok": False, "error": "unknown city"}
        with self.assertRaises(GatewayError):
            weather.get_forecast("Nowhere")


if __name__ == "__main__":
    unittest.main()
