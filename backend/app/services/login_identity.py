import re

SAMPLE_LOGIN_DOMAIN = "anuvarthan.test"
_SHORT_ID = re.compile(r"^[a-z0-9._-]{2,32}$")


def resolve_login_email(raw: str) -> str:
    value = (raw or "").strip().lower()
    if not value:
        return value
    if "@" in value:
        return value
    if _SHORT_ID.fullmatch(value):
        return f"{value}@{SAMPLE_LOGIN_DOMAIN}"
    return value
