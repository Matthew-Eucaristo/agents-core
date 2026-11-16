from email.utils import getaddresses


def deliver(message, settings, smtp_factory):
    recipients = [address for _, address in getaddresses(message.get_all("To", []))]
    with smtp_factory(settings.host, settings.port, timeout=settings.timeout) as smtp:
        if settings.starttls:
            smtp.starttls()
        if settings.username:
            smtp.login(settings.username, settings.password)
        smtp.sendmail(settings.sender, recipients, message.as_string())
