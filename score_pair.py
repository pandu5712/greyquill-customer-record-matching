"""Starter file for Part 1 of the forward deployed engineer intern task.

Fill in score_pair. Keep the two classes and the function signature as they are, because we
run our own tests against them. Add any helpers and libraries you need, and list the
libraries in your README.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from difflib import SequenceMatcher
import re
import unicodedata


@dataclass
class FieldComparison:
    """How to compare one field."""

    attribute: str
    method: str
    weight: float


@dataclass
class MatchResult:
    confidence: float
    algorithm: str
    field_scores: dict[str, float]


PLAN = [
    FieldComparison("name", "phonetic", 0.25),
    FieldComparison("email", "edit_distance", 0.20),
    FieldComparison("phone", "normalized_phone", 0.20),
    FieldComparison("date_of_birth", "date", 0.20),
    FieldComparison("pin_code", "exact", 0.10),
    FieldComparison("city", "exact", 0.05),
]


def _clean_text(value: object) -> str:
    """Normalize text for comparisons without changing its meaning."""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().strip().split())


def _is_blank(value: object) -> bool:
    return value is None or not str(value).strip() or str(value).strip().casefold() in {
        "nan", "none", "null"
    }


def _soundex(word: str) -> str:
    """Small standard-library Soundex implementation for phonetic name matching."""
    letters = re.sub(r"[^a-z]", "", word.casefold())
    if not letters:
        return ""
    codes = {
        **dict.fromkeys("bfpv", "1"),
        **dict.fromkeys("cgjkqsxz", "2"),
        **dict.fromkeys("dt", "3"),
        "l": "4", "m": "5", "n": "5", "r": "6",
    }
    first = letters[0].upper()
    result = []
    previous = codes.get(letters[0], "")
    for char in letters[1:]:
        code = codes.get(char, "")
        if code and code != previous:
            result.append(code)
        previous = code
    return (first + "".join(result) + "000")[:4]


def _name_tokens(value: str) -> list[str]:
    # "Surname, Given name" is equivalent to "Given name Surname".
    if "," in value:
        left, right = value.split(",", 1)
        value = right + " " + left
    return re.findall(r"[a-z0-9]+", _clean_text(value))


def _token_similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    # An initial should match the beginning of a full given name.
    if len(left) == 1 and right.startswith(left):
        return 0.9
    if len(right) == 1 and left.startswith(right):
        return 0.9
    if _soundex(left) and _soundex(left) == _soundex(right):
        return 0.9
    return SequenceMatcher(None, left, right).ratio()


def _phonetic_name_score(left: str, right: str) -> float:
    a_tokens = _name_tokens(left)
    b_tokens = _name_tokens(right)
    if not a_tokens or not b_tokens:
        return 0.0

    # Greedy best-token matching makes word order irrelevant.
    remaining = list(b_tokens)
    scores = []
    for token in a_tokens:
        if not remaining:
            scores.append(0.0)
            continue
        best_index = max(
            range(len(remaining)),
            key=lambda index: _token_similarity(token, remaining[index]),
        )
        scores.append(_token_similarity(token, remaining.pop(best_index)))

    # Penalize unmatched extra tokens rather than silently ignoring them.
    matched_total = sum(scores)
    return max(0.0, min(1.0, matched_total / max(len(a_tokens), len(b_tokens))))


def _edit_distance_score(left: str, right: str) -> float:
    a = re.sub(r"\s+", "", _clean_text(left))
    b = re.sub(r"\s+", "", _clean_text(right))
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _normalize_phone(value: str) -> str:
    raw = value.strip()
    # Remove the international prefix before stripping punctuation.
    if raw.startswith("+91"):
        raw = raw[3:]
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0"):
        digits = digits[1:]
    return digits


def _parse_date(value: str) -> date | None:
    text = value.strip()
    formats = (
        "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y",
        "%d-%b-%Y", "%d-%B-%Y", "%d/%b/%Y",
        "%d.%m.%y", "%d/%m/%y", "%d-%m-%y",
        "%d-%b-%y", "%d-%B-%y",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt).date()
            if "%y" in fmt:
                year = parsed.year
                # Customer birth dates in this dataset are contemporary:
                # interpret 00-30 as 2000-2030 and 31-99 as 1931-1999.
                short_year = int(text[-2:])
                year = 2000 + short_year if short_year <= 30 else 1900 + short_year
                parsed = parsed.replace(year=year)
            return parsed
        except ValueError:
            continue
    return None


def score_pair(a: dict[str, object], b: dict[str, object], plan: list[FieldComparison]) -> MatchResult:
    """Return a weighted similarity score and per-field evidence.

    Name similarity is token-order-independent. Soundex-equivalent names receive
    a strong score, and initials receive partial credit. Email similarity uses
    difflib's SequenceMatcher ratio on case-insensitive, whitespace-free text.
    """
    field_scores: dict[str, float] = {}
    weighted_total = 0.0
    compared_weight = 0.0
    methods = []

    for comparison in plan:
        attribute = comparison.attribute
        left = a.get(attribute)
        right = b.get(attribute)
        if _is_blank(left) or _is_blank(right):
            continue

        left_text, right_text = str(left).strip(), str(right).strip()
        method = comparison.method

        if method == "phonetic":
            score = _phonetic_name_score(left_text, right_text)
        elif method == "edit_distance":
            score = _edit_distance_score(left_text, right_text)
        elif method == "normalized_phone":
            left_phone = _normalize_phone(left_text)
            right_phone = _normalize_phone(right_text)
            score = float(bool(left_phone) and left_phone == right_phone)
        elif method == "date":
            left_date, right_date = _parse_date(left_text), _parse_date(right_text)
            score = float(left_date is not None and left_date == right_date)
        elif method == "exact":
            score = float(_clean_text(left_text) == _clean_text(right_text))
        else:
            raise ValueError(f"Unsupported comparison method: {method}")

        score = max(0.0, min(1.0, float(score)))
        field_scores[attribute] = score
        weight = max(0.0, float(comparison.weight))
        weighted_total += score * weight
        compared_weight += weight
        if method not in methods:
            methods.append(method)

    confidence = weighted_total / compared_weight if compared_weight else 0.0
    return MatchResult(
        confidence=max(0.0, min(1.0, confidence)),
        algorithm="+".join(methods),
        field_scores=field_scores,
    )


def main() -> None:
    """Run one comparison from a CSV file: python score_pair.py FILE.csv ID_A ID_B."""
    import argparse
    import csv
    import json

    parser = argparse.ArgumentParser(description="Compare two customer records.")
    parser.add_argument("csv_file", help="Path to the customer records CSV")
    parser.add_argument("record_id_a", help="First record_id")
    parser.add_argument("record_id_b", help="Second record_id")
    args = parser.parse_args()

    with open(args.csv_file, newline="", encoding="utf-8-sig") as handle:
        rows = {row["record_id"]: row for row in csv.DictReader(handle)}

    missing = [record_id for record_id in (args.record_id_a, args.record_id_b)
               if record_id not in rows]
    if missing:
        parser.error("Record ID(s) not found: " + ", ".join(missing))

    result = score_pair(rows[args.record_id_a], rows[args.record_id_b], PLAN)
    print(json.dumps({
        "record_ids": [args.record_id_a, args.record_id_b],
        "confidence": round(result.confidence, 4),
        "algorithm": result.algorithm,
        "field_scores": result.field_scores,
    }, indent=2))


if __name__ == "__main__":
    main()
