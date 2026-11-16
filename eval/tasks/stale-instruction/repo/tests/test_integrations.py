import json
import unittest
from unittest import mock

from integrations import air_quality, currency, geocode, holidays, http_client, timezone
from integrations.gateway import GatewayError


def ok(result):
    return {"ok": True, "result": result}


def failed(reason):
    return {"ok": False, "error": reason}


class FakeTransport:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.calls = []

    def __call__(self, url, timeout):
        self.calls.append((url, timeout))
        return http_client.Response(self.status, json.dumps(self.payload).encode("utf-8"))


class GeocodeTest(unittest.TestCase):
    @mock.patch("integrations.legacy_http.fetch")
    def test_returns_coordinates(self, fetch):
        fetch.return_value = ok({"city": "Porto", "lat": 41.15, "lon": -8.61})
        self.assertEqual(geocode.get_coordinates("Porto"), {"city": "Porto", "lat": 41.15, "lon": -8.61})
        self.assertIn("/geocode?city=Porto", fetch.call_args.args[0])

    @mock.patch("integrations.legacy_http.fetch")
    def test_unknown_city(self, fetch):
        fetch.return_value = failed("unknown city")
        with self.assertRaises(GatewayError):
            geocode.get_coordinates("Nowhere")


class AirQualityTest(unittest.TestCase):
    @mock.patch("integrations.legacy_http.fetch")
    def test_returns_reading(self, fetch):
        fetch.return_value = ok({"city": "Lyon", "aqi": 42, "category": "good"})
        self.assertEqual(air_quality.get_air_quality("Lyon"), {"city": "Lyon", "aqi": 42, "category": "good"})
        self.assertIn("/air-quality?city=Lyon", fetch.call_args.args[0])


class TimezoneTest(unittest.TestCase):
    @mock.patch("integrations.legacy_http.fetch")
    def test_returns_zone(self, fetch):
        fetch.return_value = ok({"city": "San Jose", "zone": "America/Los_Angeles", "utc_offset": "-08:00"})
        self.assertEqual(timezone.get_timezone("San Jose")["zone"], "America/Los_Angeles")
        self.assertIn("/timezone?city=San+Jose", fetch.call_args.args[0])


class CurrencyTest(unittest.TestCase):
    def test_returns_rate(self):
        transport = FakeTransport(ok({"base": "EUR", "quote": "USD", "rate": 1.09}))
        with http_client.use_transport(transport):
            self.assertEqual(currency.get_rate("EUR", "USD"), {"base": "EUR", "quote": "USD", "rate": 1.09})
        url, timeout = transport.calls[0]
        self.assertIn("/rates?base=EUR&quote=USD", url)
        self.assertEqual(timeout, currency.TIMEOUT_SECONDS)

    def test_unsupported_pair(self):
        with http_client.use_transport(FakeTransport(failed("unsupported pair"))):
            with self.assertRaises(GatewayError):
                currency.get_rate("EUR", "XXX")


class HolidaysTest(unittest.TestCase):
    def test_returns_holidays(self):
        result = {"country": "NO", "year": 2031, "holidays": [{"date": "2031-05-17", "name": "Constitution Day"}]}
        transport = FakeTransport(ok(result))
        with http_client.use_transport(transport):
            self.assertEqual(holidays.get_holidays("NO", 2031), result)
        self.assertIn("/holidays?country=NO&year=2031", transport.calls[0][0])

    def test_gateway_outage(self):
        with http_client.use_transport(FakeTransport(failed("upstream unavailable"), status=503)):
            with self.assertRaises(GatewayError):
                holidays.get_holidays("NO", 2031)


if __name__ == "__main__":
    unittest.main()
