from __future__ import annotations

from typing import Callable

from ..models import BillRecord
from .base import apply_generic_template
from .octopus import apply_octopus_template
from .acea import apply_acea_template, apply_acea_conguaglio_template
from .enel import apply_enel_template
from .iren import apply_iren_template
from .sen import apply_sen_template

TEMPLATE_APPLIERS: dict[str, Callable[[BillRecord, str, list[str]], None]] = {
    "generic":          apply_generic_template,
    "octopus":          apply_octopus_template,
    "acea":             apply_acea_template,
    "acea_standard":    apply_acea_template,
    "acea_conguaglio":  apply_acea_conguaglio_template,
    "enel":             apply_enel_template,
    "iren":             apply_iren_template,
    "sen":              apply_sen_template,
}
