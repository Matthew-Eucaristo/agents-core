class PaymentError(Exception):
    pass


class PaymentDeclined(PaymentError):
    pass


class TransportError(PaymentError):
    pass


class ConfigError(PaymentError):
    pass
