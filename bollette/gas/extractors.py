from __future__ import annotations

from ..text_utils import slug_text


def infer_gas_supplier_template(raw_text: str, lines: list[str]) -> str:
    haystack = slug_text("\n".join(lines[:80]) + "\n" + raw_text[:8000])
    if "dolomiti energia" in haystack:
        return "dolomiti_gas"
    return "generic_gas"
