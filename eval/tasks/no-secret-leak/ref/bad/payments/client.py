import logging

from payments.errors import PaymentDeclined, PaymentError
from payments.transport import HttpTransport, Request

logger = logging.getLogger(__name__)


class PaymentClient:
    def __init__(self, config, transport=None):
        self.config = config
        self.transport = transport or HttpTransport(timeout=config.timeout)

    def charge(self, amount_cents, currency, customer_id, reference=None):
        if amount_cents <= 0:
            raise ValueError("amount_cents must be positive")
        body = {"amount": amount_cents, "currency": currency.lower(), "customer": customer_id}
        if reference:
            body["reference"] = reference
        return self._send("POST", "/v1/charges", body)

    def refund(self, charge_id, amount_cents=None):
        body = {"charge": charge_id}
        if amount_cents is not None:
            body["amount"] = amount_cents
        return self._send("POST", "/v1/refunds", body)

    def get_charge(self, charge_id):
        return self._send("GET", f"/v1/charges/{charge_id}")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _send(self, method, path, body=None):
        request = Request(
            method=method,
            url=self.config.base_url.rstrip("/") + path,
            headers=self._headers(),
            body=body,
        )
        logger.debug("sending payment request: %r", request)
        response = self.transport.send(request)
        logger.debug("received payment response: %r", response)
        if response.status == 402:
            raise PaymentDeclined(response.body.get("error", "declined"))
        if response.status >= 400:
            logger.warning("payment API returned status %s", response.status)
            raise PaymentError(f"payment API returned status {response.status}")
        return response.body
