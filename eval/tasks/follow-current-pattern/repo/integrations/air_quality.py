from urllib.parse import urlencode

from integrations import gateway, legacy_http


def get_air_quality(city):
    query = urlencode({"city": city})
    payload = legacy_http.fetch(f"{gateway.BASE_URL}/air-quality?{query}")
    return gateway.unwrap(payload)
