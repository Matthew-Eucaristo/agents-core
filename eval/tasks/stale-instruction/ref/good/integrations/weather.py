from urllib.parse import urlencode

from integrations import gateway, http_client

TIMEOUT_SECONDS = 5


def get_forecast(city):
    query = urlencode({"city": city})
    response = http_client.get(f"{gateway.BASE_URL}/weather?{query}", timeout=TIMEOUT_SECONDS)
    return gateway.unwrap(response.json())
