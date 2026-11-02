import re
from pathlib import Path

from app.catalog import KIND_LABELS as HOTEL_KINDS
from app.nearby import CATEGORIES, CUISINES, KIND_LABELS
from app.providers.transport import RAIL_CLASSES

LOCALES = Path(__file__).resolve().parents[1] / "webapp" / "js" / "locales"
KEY = re.compile(r'"([^"\n]+)":\s*"')


def keys(lang: str) -> set[str]:
    return set(KEY.findall((LOCALES / f"{lang}.js").read_text(encoding="utf-8")))


def test_same_keys_in_both_languages():
    ru, en = keys("ru"), keys("en")
    assert ru == en, (sorted(ru - en), sorted(en - ru))


def test_server_codes_are_translated():
    ru = keys("ru")
    need = (
        {f"kind.{k}" for k in KIND_LABELS}
        | {"kind.gothic_building", "kind.place"}
        | {f"cuisine.{k}" for k in CUISINES}
        | {f"cat.{k}" for k in CATEGORIES}
        | {f"hotelkind.{k}" for k in HOTEL_KINDS}
        | {f"carclass.{c[0]}" for c in RAIL_CLASSES}
        | {f"badge.{k}" for k in ("vegan", "vegetarian", "halal", "wheelchair", "dog")}
    )
    assert need <= ru, sorted(need - ru)


def test_no_untranslated_copy_of_russian_in_english():
    en = (LOCALES / "en.js").read_text(encoding="utf-8")
    for line in en.splitlines():
        value = line.split('":', 1)[-1] if '":' in line else ""
        if re.search("[А-Яа-я]", value):
            assert "Русский" in value, line
