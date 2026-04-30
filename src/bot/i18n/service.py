from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("i18n")

_LOCALES_DIR = Path(__file__).parent / "locales"
_DEFAULT_LOCALE = "zh-TW"
_SUPPORTED_LOCALES = ("zh-TW", "en-US", "zh-CN")


class I18nService:
    def __init__(
        self,
        *,
        default_locale: str = _DEFAULT_LOCALE,
        supported_locales: tuple[str, ...] = _SUPPORTED_LOCALES,
        locales_dir: Path | None = None,
    ):
        self._default_locale = default_locale
        self._supported_locales = set(supported_locales)
        self._locales_dir = locales_dir or _LOCALES_DIR
        self._strings: dict[str, dict[str, Any]] = {}
        self.load_locales()

    def load_locales(self) -> None:
        for locale in self._supported_locales:
            path = self._locales_dir / f"{locale}.json"
            if not path.exists():
                logger.warning("Locale file not found: %s", path)
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    self._strings[locale] = json.load(f)
                logger.info("Loaded locale: %s", locale)
            except Exception:
                logger.error("Failed to load locale %s", locale, exc_info=True)
        self._validate_key_parity()

    def _validate_key_parity(self) -> None:
        if self._default_locale not in self._strings:
            logger.error("Default locale '%s' not loaded", self._default_locale)
            return

        def _collect_keys(d: dict, prefix: str = "") -> set[str]:
            keys: set[str] = set()
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    keys.update(_collect_keys(v, full))
                else:
                    keys.add(full)
            return keys

        base_keys = _collect_keys(self._strings[self._default_locale])
        for locale in self._supported_locales:
            if locale == self._default_locale or locale not in self._strings:
                continue
            locale_keys = _collect_keys(self._strings[locale])
            missing = base_keys - locale_keys
            extra = locale_keys - base_keys
            if missing:
                logger.warning("Locale '%s' missing %d keys: %s", locale, len(missing), sorted(missing)[:5])
            if extra:
                logger.warning("Locale '%s' has %d extra keys: %s", locale, len(extra), sorted(extra)[:5])

    def _resolve(self, key: str, locale: str) -> str | None:
        parts = key.split(".")
        node = self._strings.get(locale)
        if node is None:
            return None
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node if isinstance(node, str) else None

    def t(self, key: str, locale: str | None = None, **params: Any) -> str:
        locale = locale or self._default_locale
        value = self._resolve(key, locale)
        if value is None and locale != self._default_locale:
            logger.warning(
                "Missing i18n key '%s' for locale '%s', falling back to %s", key, locale, self._default_locale
            )
            value = self._resolve(key, self._default_locale)
        if value is None:
            logger.error("Missing i18n key '%s' (even in default locale)", key)
            return key
        if params:
            try:
                return value.format(**params)
            except (KeyError, ValueError):
                return value
        return value

    def maybe_t(self, key: str, locale: str | None = None) -> str | None:
        locale = locale or self._default_locale
        return self._resolve(key, locale) or self._resolve(key, self._default_locale)

    def resolve_locale(
        self,
        *,
        guild_id: int | None = None,
        guild_locale: str | None = None,
        interaction_locale: str | None = None,
        config_default: str | None = None,
    ) -> str:
        if guild_id is not None:
            db_locale = self._get_guild_locale_from_db(guild_id)
            if db_locale and db_locale in self._supported_locales:
                return db_locale

        for candidate in (guild_locale, interaction_locale, config_default):
            if candidate and candidate in self._supported_locales:
                return candidate

        return self._default_locale

    def _get_guild_locale_from_db(self, guild_id: int) -> str | None:
        if not hasattr(self, "_db") or self._db is None:
            return None
        try:
            settings = self._db.get_server_settings(guild_id)
            if settings and settings.get("language"):
                return settings["language"]
        except Exception:
            logger.debug("Failed to get guild locale from DB for guild %s", guild_id, exc_info=True)
        return None

    def set_db_provider(self, provider: Any) -> None:
        self._db = provider

    def get_supported_locales(self) -> list[str]:
        return sorted(self._supported_locales)
