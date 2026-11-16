from urllib.parse import urlencode

from integrations import gateway, http_client

TIMEOUT_SECONDS = 5


def get_holidays(country, year):
    query = urlencode({"country": country, "year": year})
    response = http_client.get(f"{gateway.BASE_URL}/holidays?{query}", timeout=TIMEOUT_SECONDS)
    return gateway.unwrap(response.json())
