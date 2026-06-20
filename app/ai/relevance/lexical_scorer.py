from collections import Counter
from math import sqrt
import re
import unicodedata


def lexical_similarity(left: str | None, right: str | None) -> float:
    left_tokens = _word_tokens(left)
    right_tokens = _word_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0

    token_score = _tf_cosine(left_tokens, right_tokens)
    char_score = _char_ngram_dice(left or "", right or "")
    return round(min(1.0, token_score * 0.70 + char_score * 0.30), 4)


def _normalize(text: str | None) -> str:
    value = unicodedata.normalize("NFC", text or "").lower()
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"\b10\.\d{4,9}/\S+\b", " ", value, flags=re.IGNORECASE)
    return value


def _word_tokens(text: str | None) -> list[str]:
    return [
        token
        for token in re.findall(r"[\wÀ-ỹ]+", _normalize(text), flags=re.UNICODE)
        if len(token) >= 2
    ]


def _tf_cosine(left_tokens: list[str], right_tokens: list[str]) -> float:
    left_counts = Counter(left_tokens)
    right_counts = Counter(right_tokens)
    dot = sum(value * right_counts.get(token, 0) for token, value in left_counts.items())
    left_norm = sqrt(sum(value * value for value in left_counts.values()))
    right_norm = sqrt(sum(value * value for value in right_counts.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _char_ngram_dice(left: str, right: str, n: int = 4) -> float:
    left_normalized = re.sub(r"\s+", " ", _normalize(left)).strip()
    right_normalized = re.sub(r"\s+", " ", _normalize(right)).strip()
    if len(left_normalized) < n or len(right_normalized) < n:
        return 0.0
    left_ngrams = {left_normalized[index : index + n] for index in range(len(left_normalized) - n + 1)}
    right_ngrams = {right_normalized[index : index + n] for index in range(len(right_normalized) - n + 1)}
    if not left_ngrams or not right_ngrams:
        return 0.0
    return (2 * len(left_ngrams & right_ngrams)) / (len(left_ngrams) + len(right_ngrams))
