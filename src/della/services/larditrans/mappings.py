"""Mapping dictionaries for Lardi-Trans API."""

from typing import Dict

# Maps della truck types to Lardi-Trans body type names
BODY_TYPE_MAPPING: Dict[str, str] = {
    # Direct name matches (della name == lardi name, case-insensitive)
    "тент": "тент",
    "ізотерм": "ізотерм",
    "автовоз": "автовоз",
    "бензовоз": "бензовоз",
    "бітумовоз": "бітумовоз",
    "борошновоз": "борошновоз",
    "евакуатор": "евакуатор",
    "зерновоз": "зерновоз",
    "лісовоз": "лісовоз",
    "маніпулятор": "маніпулятор",
    "масловоз": "масловоз",
    "мікроавтобус": "мікроавтобус",
    "платформа": "платформа",
    "самоскид": "самоскид",
    "скотовоз": "скотовоз",
    "тягач": "тягач",
    "контейнеровоз": "контейнеровоз",
    # Name differs between della and Lardi-Trans
    "рефрижератор": "реф.",
    "цільнометал.": "цільномет",
    "відкрита": "бортова / відкрита",
    "бортова": "бортова / відкрита",
    "контейнеровіз": "контейнеровоз",
    "контейнер пустий": "контейнер",
    "кормовіз": "кормовоз",
    "птаховіз": "птаховоз",
    "скловіз": "скловоз",
    "трубовіз": "трубовоз",
    "цементовіз": "цементовоз",
    "щеповіз": "щеповоз",
    "металовіз (ломовіз)": "ломовоз / металовоз",
    "бетонозмішувач": "бетоновоз",
    "негабарит": "трал / негабарит",
    "трал": "трал / негабарит",
    "автокран": "кран",
    "автобус вантажопас.": "автобус",
    "автобус люкс": "автобус",
    "зерновоз-самоскид": "зерновоз",
    # Cistern subtypes → specific Lardi types
    "цистерна газова": "газовоз",
    "цистерна харч.": "автоцистерна",
    "цистерна хім.": "автоцистерна",
    "цистерна ізотерм.": "автоцистерна",
    # Approximate matches (no exact Lardi equivalent)
    "цільнопластиковий": "цільномет",
    "мебльовіз": "цільномет",
    "панелевіз": "плитовоз",
    "рулоновіз": "бортова / відкрита",
    "екскаватор": "кран",
    "спецавто": "тент",
}

# Maps della price currency strings to Lardi-Trans API currency names.
# API names: "грн.", "$", "€" (as returned by /v2/references/currencies).
CURRENCY_MAPPING: Dict[str, str] = {
    "грн": "грн.",
    "uah": "грн.",
    "usd": "$",
    "$": "$",
    "eur": "€",
    "€": "€",
    "євро": "€",
}

# Maps della PriceTag strings to Lardi-Trans payment type names.
# Right-side values are matched against names from /v2/references/payment/types.
PAYMENT_FORM_MAPPING: Dict[str, str] = {
    "безготівковий": "безнал.",
    "готівка": "нал.",
    "комбінов.": "комб.",
    "софт": "эл. платеж",
    "на картку": "карта",
}

# Maps country names/codes to ISO 3166-1 alpha-2.
COUNTRY_MAPPING: Dict[str, str] = {
    "UA": "UA",
    "УКРАЇНА": "UA",
    "УКРАИНА": "UA",
    "UKRAINE": "UA",
    "PL": "PL",
    "ПОЛЬЩА": "PL",
    "ПОЛЬША": "PL",
    "POLAND": "PL",
    "DE": "DE",
    "НІМЕЧЧИНА": "DE",
    "ГЕРМАНИЯ": "DE",
    "GERMANY": "DE",
    "BY": "BY",
    "БІЛОРУСЬ": "BY",
    "БЕЛАРУСЬ": "BY",
    "BELARUS": "BY",
    "MD": "MD",
    "МОЛДОВА": "MD",
    "MOLDOVA": "MD",
    "RO": "RO",
    "РУМУНІЯ": "RO",
    "РУМЫНИЯ": "RO",
    "ROMANIA": "RO",
    "HU": "HU",
    "УГОРЩИНА": "HU",
    "ВЕНГРИЯ": "HU",
    "HUNGARY": "HU",
    "SK": "SK",
    "СЛОВАЧЧИНА": "SK",
    "СЛОВАКИЯ": "SK",
    "SLOVAKIA": "SK",
    "CZ": "CZ",
    "ЧЕХІЯ": "CZ",
    "ЧЕХИЯ": "CZ",
    "CZECHIA": "CZ",
    "LT": "LT",
    "ЛИТВА": "LT",
    "LITHUANIA": "LT",
    "LV": "LV",
    "ЛАТВІЯ": "LV",
    "ЛАТВИЯ": "LV",
    "LATVIA": "LV",
    "EE": "EE",
    "ЕСТОНІЯ": "EE",
    "ЭСТОНИЯ": "EE",
    "ESTONIA": "EE",
}

# Default IDs when reference lookup fails
DEFAULT_BODY_TYPE_ID = 1  # Тент as fallback
DEFAULT_CURRENCY_ID = 2  # грн. (UAH)
