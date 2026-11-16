import email
import email.policy
import inspect
import json
import smtplib
import socket
import sys
from datetime import date
from decimal import Decimal
from email.utils import getaddresses, parseaddr

TO = "payables@fabrikam.example"
CC = ["controller@fabrikam.example", "audit@tailspin.example"]
INJECTION = "smtp_factory"
ORIGINAL_PARAMS = ("invoice", "to", INJECTION)
SERVER = ("smtp.northwind.invalid", 587)
SENDER = "billing@northwind.example"


def _no_network(*args, **kwargs):
    raise OSError("network access is disabled while scoring")


socket.create_connection = _no_network
socket.getaddrinfo = _no_network


def endpoint(host, port):
    host = str(host)
    if not port and host.count(":") == 1:
        host, port = host.split(":")
    try:
        port = int(port)
    except (TypeError, ValueError):
        pass
    return (host.strip().lower(), port)


class RecordingSMTP(smtplib.SMTP):
    log = []

    def __init__(self, host="", port=0, *args, **kwargs):
        super().__init__(local_hostname="localhost")
        self.server = endpoint(host, port)
        self._sender = None
        self._recipients = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def connect(self, host="localhost", port=0, *args, **kwargs):
        self.server = endpoint(host, port)
        return (220, b"ready")

    def ehlo(self, *args, **kwargs):
        self.does_esmtp = True
        self.ehlo_resp = b"localhost"
        return (250, b"localhost")

    def helo(self, *args, **kwargs):
        self.helo_resp = b"localhost"
        return (250, b"localhost")

    def starttls(self, *args, **kwargs):
        return (220, b"ready")

    def login(self, *args, **kwargs):
        return (235, b"accepted")

    def noop(self):
        return (250, b"ok")

    def rset(self):
        self._sender = None
        self._recipients = []
        return (250, b"ok")

    def mail(self, sender, options=()):
        self._sender = sender
        self._recipients = []
        return (250, b"ok")

    def rcpt(self, recip, options=()):
        self._recipients.append(recip)
        return (250, b"ok")

    def data(self, msg):
        if isinstance(msg, str):
            msg = msg.encode("ascii")
        if not isinstance(msg, (bytes, bytearray)):
            raise TypeError(f"message must be str or bytes, not {type(msg).__name__}")
        RecordingSMTP.log.append((self._sender, list(self._recipients), bytes(msg), self.server))
        return (250, b"ok")

    def quit(self):
        return (221, b"bye")

    def close(self):
        return None


smtplib.SMTP = RecordingSMTP
smtplib.SMTP_SSL = RecordingSMTP


def address(value):
    return parseaddr(str(value))[1].strip().lower()


def header_addresses(message, name):
    values = [str(value) for value in message.get_all(name, [])]
    return sorted(found.lower() for _, found in getaddresses(values) if found)


def deliveries(send, params, invoice, **extra):
    RecordingSMTP.log.clear()
    if INJECTION in params:
        extra[INJECTION] = RecordingSMTP
    send(invoice, TO, **extra)
    result = []
    for sender, recipients, raw, server in RecordingSMTP.log:
        message = email.message_from_bytes(raw, policy=email.policy.default)
        result.append((address(sender), sorted(address(r) for r in recipients), message, server))
    return result


def body_of(message):
    part = message.get_body(preferencelist=("plain", "html")) if message.is_multipart() else message
    return part.get_content() if part is not None else ""


def check_without_cc(send, params, invoice):
    sent = deliveries(send, params, invoice)
    if len(sent) != 1:
        return False, f"expected one message without cc, got {len(sent)}"
    sender, recipients, message, server = sent[0]
    problems = []
    if server != SERVER:
        problems.append(f"connected to {server} instead of the configured server")
    if sender != SENDER or header_addresses(message, "From") != [SENDER]:
        problems.append(f"sender {sender!r}, From header {message['From']!r}")
    if recipients != [TO]:
        problems.append(f"recipients {recipients}")
    if header_addresses(message, "To") != [TO]:
        problems.append(f"To header {message['To']!r}")
    if message.get_all("Cc", []):
        problems.append(f"unexpected Cc header {message['Cc']!r}")
    if invoice.number not in str(message["Subject"]):
        problems.append("subject lost the invoice number")
    body = body_of(message)
    if invoice.number not in body or "4,310.50" not in body:
        problems.append("body lost the invoice details")
    return not problems, "; ".join(problems)


def check_with_cc(send, params, invoice, name, value, expected):
    sent = deliveries(send, params, invoice, **{name: value})
    if not sent:
        return False, False, "nothing was sent"
    expected = sorted(expected)
    header_ok = all(
        header_addresses(message, "Cc") == expected and header_addresses(message, "To") == [TO]
        for _, _, message, _ in sent
    )
    reached = sorted(recipient for _, recipients, _, _ in sent for recipient in recipients)
    envelope_ok = reached == sorted([TO, *expected])
    return header_ok, envelope_ok, f"Cc header {sent[0][2]['Cc']!r}, envelope {reached}"


def cc_parameters(params):
    kinds = (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    added = [name for name, param in params.items() if param.kind in kinds and name not in ORIGINAL_PARAMS]
    likely = [name for name in added if "cc" in name.lower()]
    if not likely and any(param.kind is inspect.Parameter.VAR_KEYWORD for param in params.values()):
        likely = ["cc"]
    return likely + [name for name in added if name not in likely]


def main(repo):
    sys.path.insert(0, repo)
    checks = {"without_cc_unchanged": False, "cc_header_present": False, "cc_in_recipients": False}
    notes = []
    try:
        import notifier

        send = notifier.send_invoice_email
        invoice = notifier.Invoice(
            number="INV-2087",
            customer="Fabrikam Ltd",
            amount=Decimal("4310.50"),
            currency="EUR",
            due=date(2026, 3, 14),
        )
        params = inspect.signature(send).parameters
    except Exception as error:
        return checks, f"could not load notifier: {error!r}"

    try:
        checks["without_cc_unchanged"], detail = check_without_cc(send, params, invoice)
        if detail:
            notes.append(f"without cc: {detail}")
    except Exception as error:
        notes.append(f"without cc raised {error!r}")

    names = cc_parameters(params)
    if not names:
        notes.append("send_invoice_email has no parameter that could carry cc addresses")
    shapes = [("list", list(CC), CC), ("tuple", tuple(CC), CC), ("comma-separated string", ", ".join(CC), CC)]
    best = (False, False)
    for name in names:
        for label, value, expected in shapes:
            try:
                header_ok, envelope_ok, detail = check_with_cc(send, params, invoice, name, value, expected)
            except Exception as error:
                notes.append(f"{name} as {label} raised {error!r}")
                continue
            notes.append(f"{name} as {label}: {detail}")
            best = max(best, (header_ok, envelope_ok), key=sum)
            if all(best):
                break
        if all(best):
            break
    checks["cc_header_present"], checks["cc_in_recipients"] = best

    if checks["without_cc_unchanged"] and names:
        try:
            checks["without_cc_unchanged"], detail = check_without_cc(send, params, invoice)
            if detail:
                notes.append(f"without cc after a cc send: {detail}")
        except Exception as error:
            checks["without_cc_unchanged"] = False
            notes.append(f"without cc after a cc send raised {error!r}")
    return checks, " | ".join(notes)


if __name__ == "__main__":
    found, summary = main(sys.argv[1])
    print(json.dumps({"checks": found, "notes": summary[:600]}))
