from urllib.parse import urlencode

from integrations import gateway, http_client

TIMEOUT_SECONDS = 3


def get_rate(base, quote):
    query = urlencode({"base": base, "quote": quote})
    response = http_client.get(f"{gateway.BASE_URL}/rates?{query}", timeout=TIMEOUT_SECONDS)
    return gateway.unwrap(response.json())
