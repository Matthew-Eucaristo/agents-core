from urllib.parse import urlencode

from integrations import gateway, legacy_http


def get_forecast(city):
    query = urlencode({"city": city})
    payload = legacy_http.fetch(f"{gateway.BASE_URL}/weather?{query}")
    return gateway.unwrap(payload)
