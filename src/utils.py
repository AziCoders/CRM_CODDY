import re
from typing import Any, Dict, Optional, List

# ==============================================================================
# Phone Normalization
# ==============================================================================

def normalize_phone(phone: str) -> str:
    """
    Validates and normalizes a phone number to the format +7XXXXXXXXXX.
    Returns an empty string if the number is invalid.
    """
    if not phone:
        return ""

    digits = re.sub(r"\D", "", phone)  # Remove everything except digits
    if len(digits) == 11:
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        if digits.startswith("7"):
            return f"+{digits}"
    return ""

# ==============================================================================
# Notion Property Builders
# ==============================================================================

def build_rich_text(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {"rich_text": []}
    return {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": value},
            }
        ]
    }

def build_title(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {"title": []}
    return {
        "title": [
            {
                "type": "text",
                "text": {"content": value},
            }
        ]
    }

def build_select(value: Optional[str]) -> Dict[str, Any]:
    return {"select": {"name": value}} if value else {"select": None}

def build_date(value: Optional[str]) -> Dict[str, Any]:
    return {"date": {"start": value}} if value else {"date": None}

def build_phone(value: Optional[str]) -> Dict[str, Any]:
    return {"phone_number": value or None}

def build_number(value: Optional[Any]) -> Dict[str, Any]:
    return {"number": value if value not in ("", None) else None}

def build_relation(ids: Optional[List[str]]) -> Dict[str, Any]:
    return {"relation": [{"id": _id} for _id in ids]} if ids else {"relation": []}
