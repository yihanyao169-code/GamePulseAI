from __future__ import annotations

import re

from src.models import ReviewItem


HAN_RE = re.compile(r"[\u4e00-\u9fff]")
HIRAGANA_RE = re.compile(r"[\u3040-\u309f]")
KATAKANA_RE = re.compile(r"[\u30a0-\u30ff]")
HANGUL_RE = re.compile(r"[\uac00-\ud7af]")
THAI_RE = re.compile(r"[\u0e00-\u0e7f]")
LATIN_RE = re.compile(r"[A-Za-z]")


def filter_reviews_by_language(
    reviews: list[ReviewItem],
    language_code: str,
) -> tuple[list[ReviewItem], int]:
    matched = [review for review in reviews if is_language_match(review.content, language_code)]
    return matched, len(reviews) - len(matched)


def is_language_match(text: str, language_code: str) -> bool:
    latin_language_codes = {"en", "fr", "de", "es", "pt", "vi", "id", "ms", "it", "pl"}
    if language_code not in {"zh", "ja", "ko", "th", *latin_language_codes}:
        return True

    han = len(HAN_RE.findall(text))
    hiragana = len(HIRAGANA_RE.findall(text))
    katakana = len(KATAKANA_RE.findall(text))
    hangul = len(HANGUL_RE.findall(text))
    thai = len(THAI_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    language_chars = han + hiragana + katakana + hangul + thai + latin

    if language_chars == 0:
        return False

    if language_code == "zh":
        return han > 0 and hiragana == 0 and katakana == 0 and hangul == 0 and han >= latin
    if language_code in latin_language_codes:
        return latin > 0 and latin / language_chars >= 0.6 and hiragana == 0 and katakana == 0 and hangul == 0
    if language_code == "ja":
        japanese = hiragana + katakana
        return japanese > 0 and (japanese + han) / language_chars >= 0.5 and hangul == 0
    if language_code == "ko":
        return hangul > 0 and hangul / language_chars >= 0.5
    if language_code == "th":
        return thai > 0 and thai / language_chars >= 0.5

    return True
