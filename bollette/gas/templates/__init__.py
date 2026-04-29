from __future__ import annotations

from typing import Callable

from ..models import GasBillRecord
from .base import apply_generic_gas_template
from .dolomiti import apply_dolomiti_gas_template


GAS_TEMPLATE_APPLIERS: dict[str, Callable[[GasBillRecord, str, list[str]], None]] = {
    "generic_gas": apply_generic_gas_template,
    "dolomiti_gas": apply_dolomiti_gas_template,
}
