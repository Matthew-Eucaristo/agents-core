from shared.limits import BIO_MAX_LENGTH, DISPLAY_NAME_MAX_LENGTH


def normalize_display_name(raw):
    name = " ".join(raw.split())
    if not name:
        raise ValueError("Display name is required.")
    if len(name) > DISPLAY_NAME_MAX_LENGTH:
        raise ValueError(f"Display name must be {DISPLAY_NAME_MAX_LENGTH} characters or fewer.")
    return name


def characters_remaining(raw):
    return DISPLAY_NAME_MAX_LENGTH - len(" ".join(raw.split()))


def initials(name):
    words = name.split()
    if len(words) == 1:
        return words[0][0].upper()
    return (words[0][0] + words[-1][0]).upper()


def summarize_bio(bio):
    summary = " ".join(bio.split())
    if len(summary) > BIO_MAX_LENGTH:
        summary = summary[: BIO_MAX_LENGTH - 3].rstrip() + "..."
    return summary


def profile_card(display_name, bio=""):
    name = normalize_display_name(display_name)
    return {"title": name, "initials": initials(name), "summary": summarize_bio(bio)}
