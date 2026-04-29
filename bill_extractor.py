#!/usr/bin/env python3
"""CLI entry point — logica di parsing in bollette/."""
from __future__ import annotations

import argparse
from pathlib import Path

from bollette import (
    build_gas_record,
    build_record,
    discover_pdfs,
    export_xlsx,
    group_pdfs_by_service,
    load_output_config,
)
from bollette.models import ELECTRICITY_SERVICE_TYPE, GAS_SERVICE_TYPE

# Re-export per compatibilità con gui_bollette e webapp
from bollette import BillRecord, OUTPUT_COLUMNS  # noqa: F401


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estrae dati chiave da bollette PDF e li salva in XLSX."
    )
    parser.add_argument("input_path", help="Percorso a un PDF o a una cartella contenente PDF.")
    parser.add_argument(
        "-o",
        "--output",
        default="output/bollette_estratte.xlsx",
        help="Percorso output (.xlsx). Contiene un foglio per elettricità e uno per gas.",
    )
    parser.add_argument(
        "-e",
        "--electricity-config",
        help="File JSON opzionale per scegliere sottoinsieme, ordine e titoli delle colonne elettricità.",
    )
    parser.add_argument(
        "-g",
        "--gas-config",
        help="File JSON opzionale per scegliere sottoinsieme, ordine e titoli delle colonne gas.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_path).expanduser().resolve()
    output_path = Path(args.output).expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    output_path = output_path.resolve()

    electricity_config_path = _resolve_config_path(args.electricity_config)
    gas_config_path = _resolve_config_path(args.gas_config)

    try:
        electricity_columns = load_output_config(electricity_config_path, ELECTRICITY_SERVICE_TYPE)
        gas_columns = load_output_config(gas_config_path, GAS_SERVICE_TYPE)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Configurazione output non valida: {exc}") from exc

    pdfs = discover_pdfs(input_path)
    if not pdfs:
        raise SystemExit("Nessun PDF trovato nel percorso indicato.")

    grouped = group_pdfs_by_service(pdfs)
    electricity_pdfs = grouped.get(ELECTRICITY_SERVICE_TYPE, [])
    gas_pdfs = grouped.get(GAS_SERVICE_TYPE, [])

    if not electricity_pdfs and not gas_pdfs:
        raise SystemExit("Nessun dato estratto.")

    if output_path.suffix.lower() != ".xlsx":
        raise SystemExit("Formato output non supportato. Usa .xlsx")

    sheets = []
    if electricity_pdfs:
        records = [build_record(pdf) for pdf in electricity_pdfs]
        sheets.append(("Elettricità", records, electricity_columns, ELECTRICITY_SERVICE_TYPE))
    if gas_pdfs:
        records = [build_gas_record(pdf) for pdf in gas_pdfs]
        sheets.append(("Gas", records, gas_columns, GAS_SERVICE_TYPE))

    export_xlsx(sheets, output_path)
    print(f"Creato: {output_path}")
    print(f"Fogli: {', '.join(s[0] for s in sheets)}")
    print(f"PDF elaborati: {len(electricity_pdfs) + len(gas_pdfs)}")


def _resolve_config_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    return Path(raw_path).expanduser().resolve()


if __name__ == "__main__":
    main()
