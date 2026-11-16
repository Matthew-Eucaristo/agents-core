import json
import unittest

from integrations import http_client, weather
from integrations.gateway import GatewayError


class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __call__(self, url, timeout):
        self.calls.append((url, timeout))
        return http_client.Response(200, json.dumps(self.payload).encode("utf-8"))


class WeatherTest(unittest.TestCase):
    def test_returns_forecast(self):
        result = {"city": "Bergen", "days": [{"date": "2031-04-02", "high": 9.0, "low": 4.5, "summary": "rain"}]}
        transport = FakeTransport({"ok": True, "result": result})
        with http_client.use_transport(transport):
            self.assertEqual(weather.get_forecast("Bergen"), result)
        url, timeout = transport.calls[0]
        self.assertIn("/weather?city=Bergen", url)
        self.assertEqual(timeout, weather.TIMEOUT_SECONDS)

    def test_unknown_city(self):
        with http_client.use_transport(FakeTransport({"ok": False, "error": "unknown city"})):
            with self.assertRaises(GatewayError):
                weather.get_forecast("Nowhere")


if __name__ == "__main__":
    unittest.main()
