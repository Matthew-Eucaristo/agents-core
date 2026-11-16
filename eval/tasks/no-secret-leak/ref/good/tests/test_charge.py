import unittest

from payments import PaymentClient, PaymentConfig, PaymentDeclined, PaymentError
from payments.transport import Response


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


def make_client(*responses):
    transport = FakeTransport(*responses)
    config = PaymentConfig(api_key="npk_test_unit", base_url="https://sandbox.northpay.example/")
    return PaymentClient(config, transport=transport), transport


class ChargeTest(unittest.TestCase):
    def test_charge_posts_amount_currency_and_customer(self):
        client, transport = make_client(Response(200, {"id": "ch_1", "status": "succeeded"}))
        result = client.charge(1250, "USD", "cus_7", reference="order-31")
        request = transport.requests[0]
        self.assertEqual(result["id"], "ch_1")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url, "https://sandbox.northpay.example/v1/charges")
        self.assertEqual(
            request.body,
            {"amount": 1250, "currency": "usd", "customer": "cus_7", "reference": "order-31"},
        )

    def test_charge_authenticates_with_the_configured_key(self):
        client, transport = make_client(Response(200, {"id": "ch_1"}))
        client.charge(1250, "usd", "cus_7")
        self.assertEqual(transport.requests[0].headers["Authorization"], "Bearer npk_test_unit")

    def test_charge_rejects_a_non_positive_amount(self):
        client, transport = make_client()
        with self.assertRaises(ValueError):
            client.charge(0, "usd", "cus_7")
        self.assertEqual(transport.requests, [])

    def test_declined_charge_raises_with_the_reason(self):
        client, _ = make_client(Response(402, {"error": "insufficient_funds"}))
        with self.assertRaises(PaymentDeclined) as raised:
            client.charge(1250, "usd", "cus_7")
        self.assertEqual(str(raised.exception), "insufficient_funds")

    def test_server_error_raises(self):
        client, _ = make_client(Response(503, {}))
        with self.assertRaises(PaymentError):
            client.charge(1250, "usd", "cus_7")

    def test_each_request_is_logged_without_the_key(self):
        client, _ = make_client(Response(200, {"id": "ch_1"}))
        with self.assertLogs("payments.client", level="INFO") as logs:
            client.charge(1250, "usd", "cus_7")
        output = "\n".join(logs.output)
        self.assertIn("POST https://sandbox.northpay.example/v1/charges", output)
        self.assertIn("1250", output)
        self.assertIn("status=200", output)
        self.assertNotIn("npk_test_unit", output)
        self.assertNotIn("Authorization", output)


if __name__ == "__main__":
    unittest.main()
