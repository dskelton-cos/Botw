"""The game's text languages (Pack/Bootup_<code>.pack) and which one Savage Wind is set to.

Savage Wind's savagewind.ini has `text_language = auto` or one of the game's codes (USen, EUde, JPja, ...).
`auto` follows the system's display language. The map data and quests are built in that language unless the
user picks another one in Settings.
"""
import os
import re
from pathlib import Path

DEFAULT = 'USen'
# game code -> name shown in Settings (in that language)
LANGUAGES = {
    'USen': 'English (US)', 'EUen': 'English (UK)', 'USfr': 'Français (Canada)', 'EUfr': 'Français',
    'EUde': 'Deutsch', 'USes': 'Español (Latinoamérica)', 'EUes': 'Español (España)', 'EUit': 'Italiano',
    'EUnl': 'Nederlands', 'USpt': 'Português (Brasil)', 'EUru': 'Русский', 'JPja': '日本語', 'KRko': '한국어',
    'CNzh': '简体中文', 'TWzh': '繁體中文', 'THth': 'ไทย',
}
# game code -> browser locale, for the page's own words, dates and numbers
LOCALES = {
    'USen': 'en-US', 'EUen': 'en-GB', 'USfr': 'fr-CA', 'EUfr': 'fr-FR', 'EUde': 'de-DE', 'USes': 'es-419',
    'EUes': 'es-ES', 'EUit': 'it-IT', 'EUnl': 'nl-NL', 'USpt': 'pt-BR', 'EUru': 'ru-RU', 'JPja': 'ja-JP',
    'KRko': 'ko-KR', 'CNzh': 'zh-CN', 'TWzh': 'zh-TW', 'THth': 'th-TH',
}
_LATAM_ES = {'419', 'MX', 'US', 'AR', 'CL', 'CO', 'PE', 'VE', 'EC', 'GT', 'CU', 'BO', 'DO', 'HN', 'PY', 'SV', 'NI',
             'CR', 'PR', 'PA', 'UY'}


def from_locale(tag):
    """'de-DE' / 'en-US' / 'ja' / 'zh-Hant' / 'es-419' / 'fr_CA' / 'USen' -> game code, or None."""
    if not tag:
        return None
    if tag in LANGUAGES:
        return tag
    parts = re.split(r'[-_]', tag.strip())
    lang = parts[0].lower()
    rest = [p for p in parts[1:] if p]
    region = next((p.upper() for p in rest if len(p) == 2 or (len(p) == 3 and p.isdigit())), '')
    script = next((p.title() for p in rest if len(p) == 4), '')
    if lang == 'en':
        return 'EUen' if region in ('GB', 'IE', 'AU', 'NZ') else 'USen'
    if lang == 'fr':
        return 'USfr' if region == 'CA' else 'EUfr'
    if lang == 'es':
        return 'USes' if region in _LATAM_ES else 'EUes'
    if lang == 'pt':
        return 'USpt'
    if lang == 'zh':
        return 'TWzh' if script == 'Hant' or region in ('TW', 'HK', 'MO') else 'CNzh'
    return {'de': 'EUde', 'it': 'EUit', 'nl': 'EUnl', 'ru': 'EUru', 'ja': 'JPja', 'ko': 'KRko', 'th': 'THth'}.get(lang)


def system_locale():
    """The user's display language: Windows' own, elsewhere from LC_ALL / LC_MESSAGES / LANG."""
    if os.name == 'nt':
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(85)
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if ctypes.windll.kernel32.LCIDToLocaleName(lcid, buf, 85, 0):
                return buf.value
        except Exception:
            return None
        return None
    for var in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        tag = re.split(r'[.@]', os.environ.get(var, ''))[0]
        if tag and tag not in ('C', 'POSIX'):
            return tag
    return None


def recomp_setting(data_dir):
    """The `text_language` value in Savage Wind's savagewind.ini ('auto' or a code), or None without the file."""
    try:
        lines = (Path(data_dir) / 'savagewind.ini').read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return None
    for line in lines:
        line = line.split('#', 1)[0].strip()
        if '=' in line:
            key, value = (s.strip() for s in line.split('=', 1))
            if key == 'text_language':
                return value.strip('"\'')
    return 'auto'


def game_language(data_dir):
    """The language Savage Wind shows the game text in: its setting, else the system language."""
    setting = recomp_setting(data_dir) if data_dir else None
    return (from_locale(setting) if setting and setting != 'auto' else None) or from_locale(system_locale()) or DEFAULT


def available(romfs):
    """Language codes the game files have text for."""
    return sorted(c for c in LANGUAGES if romfs.exists(f'Pack/Bootup_{c}.pack'))
