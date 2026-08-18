# File: app/translations/__init__.py
"""Localization manager providing string retrieval and multi-language key resolution."""

from app.translations.am import STRINGS as AM_STRINGS
from app.translations.en import STRINGS as EN_STRINGS

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": EN_STRINGS,
    "am": AM_STRINGS,
}


def t(key: str, lang: str = "en", **kwargs: str) -> str:
    """Retrieves localized text string with automatic fallback to English."""
    lang_dict = TRANSLATIONS.get(lang, EN_STRINGS)
    template = lang_dict.get(key, EN_STRINGS.get(key, key))
    if kwargs:
        return template.format(**kwargs)
    return template


def get_all_button_texts(key: str) -> list[str]:
    """Returns all localized text variations for a button key to support pattern matching."""
    return [strings[key] for strings in TRANSLATIONS.values() if key in strings]