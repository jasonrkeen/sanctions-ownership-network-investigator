from __future__ import annotations

import re
import unicodedata


LEGAL_SUFFIXES = {
    "AG",
    "BV",
    "CORP",
    "CORPORATION",
    "CO",
    "COMPANY",
    "GMBH",
    "INC",
    "INCORPORATED",
    "JSC",
    "LIMITED",
    "LLC",
    "LLP",
    "LTD",
    "NV",
    "PLC",
    "PJSC",
    "SA",
    "SARL",
}


def transliterate(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(value: str) -> str:
    value = transliterate(value).upper()
    value = value.replace("&", " AND ")
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_name(value: str, strip_legal_suffixes: bool = False) -> str:
    normalized = normalize_text(value)
    if not strip_legal_suffixes:
        return normalized
    tokens = [token for token in normalized.split() if token not in LEGAL_SUFFIXES]
    return " ".join(tokens)


def normalize_country(value: str) -> str:
    aliases = {
        "U S": "UNITED STATES",
        "U S A": "UNITED STATES",
        "USA": "UNITED STATES",
        "UNITED STATES OF AMERICA": "UNITED STATES",
        "UK": "UNITED KINGDOM",
        "U K": "UNITED KINGDOM",
    }
    normalized = normalize_text(value)
    return aliases.get(normalized, normalized)


def normalized_tokens(value: str, strip_legal_suffixes: bool = True) -> set[str]:
    return set(normalize_name(value, strip_legal_suffixes).split())
