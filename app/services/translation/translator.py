import os
from pathlib import Path

from app.core.config import settings


class UnsupportedLanguagePair(ValueError):
    pass


def _configure_argos_directories() -> None:
    root = Path(settings.argos_data_directory).resolve()
    os.environ.setdefault("XDG_DATA_HOME", str(root / "data"))
    os.environ.setdefault("XDG_CONFIG_HOME", str(root / "config"))
    os.environ.setdefault("XDG_CACHE_HOME", str(root / "cache"))


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    if source_lang == target_lang:
        return text
    _configure_argos_directories()
    try:
        import argostranslate.translate
    except ImportError as exc:
        raise UnsupportedLanguagePair(
            "No Argos Translate language packs are installed"
        ) from exc

    languages = {
        language.code: language
        for language in argostranslate.translate.get_installed_languages()
    }
    source = languages.get(source_lang)
    target = languages.get(target_lang)
    if source is None or target is None:
        raise UnsupportedLanguagePair(
            f"Unsupported or uninstalled language pair: {source_lang}->{target_lang}"
        )
    translation = source.get_translation(target)
    if translation is None:
        raise UnsupportedLanguagePair(
            f"Unsupported or uninstalled language pair: {source_lang}->{target_lang}"
        )
    return translation.translate(text)


def supported_languages() -> list[dict[str, str]]:
    _configure_argos_directories()
    try:
        import argostranslate.translate
    except ImportError:
        return []
    return sorted(
        (
            {"code": language.code, "name": language.name}
            for language in argostranslate.translate.get_installed_languages()
        ),
        key=lambda language: (language["name"].casefold(), language["code"]),
    )
