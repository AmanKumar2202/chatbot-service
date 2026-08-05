import re


LINE_ITEM_PATTERN = re.compile(
    r"^(?!\s*(?:subtotal|tax|tip|gratuity|total)\b)"
    r"(?P<name>[A-Za-z][\w &'()./-]{1,60}?)\s+\$?(?P<price>\d+\.\d{2})\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _find_labeled_amount(text: str, labels: list[str]) -> float | None:
    labels_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"^\s*(?:{labels_pattern})\s*:?\s*\$?(?P<amount>\d+\.\d{{2}})\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return float(match.group("amount")) if match else None


def _estimate_confidence(
    items: list[dict[str, float | str]],
    subtotal: float | None,
    tax: float | None,
    tip: float | None,
    total: float | None,
) -> float:
    if not items:
        return 0.0
    score = 0.35
    item_sum = sum(float(item["price"]) for item in items)
    if subtotal is not None:
        tolerance = max(0.05, subtotal * 0.02)
        score += 0.35 if abs(item_sum - subtotal) <= tolerance else 0.05
    if total is not None:
        expected = (subtotal if subtotal is not None else item_sum) + (tax or 0) + (tip or 0)
        tolerance = max(0.05, total * 0.02)
        score += 0.30 if abs(expected - total) <= tolerance else 0.05
    return round(min(score, 1.0), 2)


def parse_receipt(ocr_text: str) -> dict:
    items = [
        {
            "name": match.group("name").strip(),
            "price": float(match.group("price")),
        }
        for match in LINE_ITEM_PATTERN.finditer(ocr_text)
    ]
    subtotal = _find_labeled_amount(ocr_text, ["subtotal"])
    tax = _find_labeled_amount(ocr_text, ["tax"])
    tip = _find_labeled_amount(ocr_text, ["tip", "gratuity"])
    total = _find_labeled_amount(ocr_text, ["total"])
    return {
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "tip": tip,
        "total": total,
        "parse_confidence": _estimate_confidence(items, subtotal, tax, tip, total),
    }
