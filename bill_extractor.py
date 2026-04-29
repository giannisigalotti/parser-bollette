#!/usr/bin/env python3
"""CLI entry point — logica di parsing in bollette/."""
from __future__ import annotations

import argparse
from pathlib import Path

from bollette import build_record, discover_pdfs, export_csv, export_xlsx, load_output_config

# Re-export per compatibilità con gui_bollette e webapp
from bollette import BillRecord, OUTPUT_COLUMNS  # noqa: F401


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estrae dati chiave da bollette luce PDF e li salva in CSV o XLSX."
    )
    parser.add_argument("input_path", help="Percorso a un PDF o a una cartella contenente PDF.")
    parser.add_argument(
        "-o",
        "--output",
        default="output/bollette_estratte.csv",
        help="Percorso del file di output. Estensioni supportate: .csv, .xlsx",
    )
    parser.add_argument(
        "-c",
        "--config",
        help=(
            "File JSON opzionale per scegliere sottoinsieme, ordine e titoli delle colonne "
            "dell'output."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_path).expanduser().resolve()
    output_path = Path(args.output).expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    output_path = output_path.resolve()
    config_path = Path(args.config).expanduser().resolve() if args.config else None
    try:
        output_columns = load_output_config(config_path)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Configurazione output non valida: {exc}") from exc

    pdfs = discover_pdfs(input_path)
    if not pdfs:
        raise SystemExit("Nessun PDF trovato nel percorso indicato.")

    records = [build_record(pdf) for pdf in pdfs]

    suffix = output_path.suffix.lower()
    if suffix == ".csv":
        export_csv(records, output_path, output_columns)
    elif suffix == ".xlsx":
        export_xlsx(records, output_path, output_columns)
    else:
        raise SystemExit("Formato output non supportato. Usa .csv oppure .xlsx")

    print(f"Creato: {output_path}")
    print(f"PDF elaborati: {len(records)}")


if __name__ == "__main__":
    main()
