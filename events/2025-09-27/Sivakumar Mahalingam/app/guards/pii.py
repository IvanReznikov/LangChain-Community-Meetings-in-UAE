import re
from typing import Dict, List, Tuple

PII_PATTERNS = {
    "PAN": r"\b(?:\d[ -]*?){13,19}\b",
    "IBAN": r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "EID": r"\b784-\d{4}-\d{7}-\d{1}\b",
}

MASK_TOKENS = {
    "PAN": "**** **** **** ####",
    "IBAN": "****-IBAN-****-####",
    "SSN": "***-**-####",
    "EID": "EID-****####",
}

def pii_redact(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """Returns (redacted_text, redaction_map)."""
    redactions: List[Dict[str, str]] = []
    redacted = text
    for pii_type, pattern in PII_PATTERNS.items():
        def _mask(m):
            s = m.group(0)
            masked = MASK_TOKENS[pii_type]
            tail = s[-4:] if len(s) >= 4 else s
            return masked.replace("####", tail)
        before = redacted
        redacted = re.sub(pattern, _mask, redacted)
        if before != redacted:
            redactions.append({
                "type": pii_type,
                "original_snippet": "<hidden>",
                "mask_pattern": MASK_TOKENS[pii_type],
            })
    return redacted, redactions
