from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ELECTRICITY_SERVICE_TYPE, GAS_SERVICE_TYPE
from .electricity.models import OUTPUT_COLUMNS
from .gas.models import GAS_OUTPUT_COLUMNS


@dataclass(frozen=True)
class OutputColumn:
    source: str
    title: str | None = None
    optional: bool = False


def load_output_config_label(config_path: Path) -> str:
    try:
        with config_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError):
        return config_path.name
    if not isinstance(payload, dict):
        return config_path.name
    label = payload.get("description") or payload.get("label") or payload.get("name") or payload.get("title")
    return label.strip() if isinstance(label, str) and label.strip() else config_path.name


def default_output_columns(service_type: str = ELECTRICITY_SERVICE_TYPE) -> list[OutputColumn]:
    return [OutputColumn(source=col) for col in output_columns_for_service(service_type)]


def load_output_config(
    config_path: Path | None,
    service_type: str = ELECTRICITY_SERVICE_TYPE,
) -> list[OutputColumn]:
    if config_path is None:
        return default_output_columns(service_type)

    with config_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict):
        config_service = payload.get("service_type") or payload.get("domain")
        if config_service and config_service != service_type:
            raise ValueError(
                f"Il file di configurazione e' per '{config_service}', non per '{service_type}'."
            )

    columns_payload = payload.get("columns") if isinstance(payload, dict) else payload
    if not isinstance(columns_payload, list) or not columns_payload:
        raise ValueError("Il file di configurazione deve contenere una lista non vuota 'columns'.")

    columns = [_parse_column(item, idx) for idx, item in enumerate(columns_payload, start=1)]
    _validate_columns(columns, service_type)
    return columns


def _parse_column(item: Any, idx: int) -> OutputColumn:
    if isinstance(item, str):
        return OutputColumn(source=item)

    if isinstance(item, dict):
        source = item.get("source") or item.get("field") or item.get("name")
        title = item.get("title") or item.get("header")
        optional = item.get("optional", False)
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"Colonna #{idx}: manca il campo 'source'.")
        if title is not None and not isinstance(title, str):
            raise ValueError(f"Colonna #{idx}: il campo 'title' deve essere una stringa.")
        if not isinstance(optional, bool):
            raise ValueError(f"Colonna #{idx}: il campo 'optional' deve essere booleano.")
        return OutputColumn(source=source.strip(), title=title.strip() if title else None, optional=optional)

    raise ValueError(f"Colonna #{idx}: formato non supportato.")


def _validate_columns(columns: list[OutputColumn], service_type: str) -> None:
    valid = set(output_columns_for_service(service_type))
    seen: set[str] = set()
    invalid: list[str] = []
    duplicates: list[str] = []

    for column in columns:
        if column.source not in valid:
            invalid.append(column.source)
        if column.source in seen:
            duplicates.append(column.source)
        seen.add(column.source)

    if invalid:
        raise ValueError("Colonne non riconosciute: " + ", ".join(invalid))
    if duplicates:
        raise ValueError("Colonne duplicate: " + ", ".join(duplicates))


def output_columns_for_service(service_type: str) -> list[str]:
    if service_type == ELECTRICITY_SERVICE_TYPE:
        return OUTPUT_COLUMNS
    if service_type == GAS_SERVICE_TYPE:
        return GAS_OUTPUT_COLUMNS
    raise ValueError(f"Tipo servizio non supportato: {service_type}")
