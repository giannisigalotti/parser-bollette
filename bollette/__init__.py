"""Public API del package bollette."""

from .models import ELECTRICITY_SERVICE_TYPE, GAS_SERVICE_TYPE  # noqa: F401
from .electricity.models import BillRecord, OUTPUT_COLUMNS, NUMERIC_COLUMNS
from .electricity.builder import build_record
from .gas.models import GasBillRecord, GAS_OUTPUT_COLUMNS, GAS_NUMERIC_COLUMNS
from .gas.builder import build_gas_record
from .discovery import classify_pdf, discover_pdfs, group_pdfs_by_service
from .exporters import export_xlsx, SheetSpec
from .output_config import OutputColumn, load_output_config, load_output_config_label

__all__ = [
    "BillRecord",
    "GasBillRecord",
    "OUTPUT_COLUMNS",
    "NUMERIC_COLUMNS",
    "GAS_OUTPUT_COLUMNS",
    "GAS_NUMERIC_COLUMNS",
    "OutputColumn",
    "build_record",
    "build_gas_record",
    "classify_pdf",
    "discover_pdfs",
    "group_pdfs_by_service",
    "export_xlsx",
    "SheetSpec",
    "load_output_config",
    "load_output_config_label",
]
