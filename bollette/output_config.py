from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import OUTPUT_COLUMNS


@dataclass(frozen=True)
class OutputColumn:
    source: str
    title: str | None = None


def default_output_columns() -> list[OutputColumn]:
    return [OutputColumn(source=col) for col in OUTPUT_COLUMNS]


def load_output_config(config_path: Path | None) -> list[OutputColumn]:
    if config_path is None:
        return default_output_columns()

    with config_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    columns_payload = payload.get("columns") if isinstance(payload, dict) else payload
    if not isinstance(columns_payload, list) or not columns_payload:
        raise ValueError("Il file di configurazione deve contenere una lista non vuota 'columns'.")

    columns = [_parse_column(item, idx) for idx, item in enumerate(columns_payload, start=1)]
    _validate_columns(columns)
    return columns


def _parse_column(item: Any, idx: int) -> OutputColumn:
    if isinstance(item, str):
        return OutputColumn(source=item)

    if isinstance(item, dict):
        source = item.get("source") or item.get("field") or item.get("name")
        title = item.get("title") or item.get("header")
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"Colonna #{idx}: manca il campo 'source'.")
        if title is not None and not isinstance(title, str):
            raise ValueError(f"Colonna #{idx}: il campo 'title' deve essere una stringa.")
        return OutputColumn(source=source.strip(), title=title.strip() if title else None)

    raise ValueError(f"Colonna #{idx}: formato non supportato.")


def _validate_columns(columns: list[OutputColumn]) -> None:
    valid = set(OUTPUT_COLUMNS)
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
