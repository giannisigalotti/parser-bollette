#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import io
import json
import os
import shutil
import tempfile
import urllib.parse
import uuid
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd
from email.parser import BytesParser
from email.policy import default as default_policy

from bill_extractor import OUTPUT_COLUMNS, build_record


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
BASE_DIR = Path(__file__).resolve().parent
WEBAPP_DIR = BASE_DIR / "output" / "webapp"
UPLOADS_DIR = WEBAPP_DIR / "uploads"
EXPORTS_DIR = WEBAPP_DIR / "exports"


def ensure_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    clean = Path(name).name.replace("\x00", "")
    return clean or f"upload-{uuid.uuid4().hex}.pdf"


def parse_multipart(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    content_type = handler.headers.get("Content-Type", "")
    content_length = int(handler.headers.get("Content-Length", "0"))
    body = handler.rfile.read(content_length)
    full_message = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    msg = BytesParser(policy=default_policy).parsebytes(full_message)

    fields: dict[str, object] = {"files": []}
    for part in msg.iter_parts():
        disposition = part.get_content_disposition()
        if disposition != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            fields["files"].append({"name": name, "filename": filename, "content": payload})
        elif name:
            fields[name] = payload.decode("utf-8", errors="replace")
    return fields


def save_uploaded_files(files: list[dict[str, object]]) -> list[Path]:
    batch_dir = UPLOADS_DIR / uuid.uuid4().hex
    batch_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for entry in files:
        filename = sanitize_filename(str(entry["filename"]))
        path = batch_dir / filename
        path.write_bytes(entry["content"])  # type: ignore[arg-type]
        saved.append(path)
    return saved


def export_records(records: list[dict[str, str]], fmt: str) -> Path:
    export_id = uuid.uuid4().hex
    out_dir = EXPORTS_DIR / export_id
    out_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(records, columns=OUTPUT_COLUMNS)
    if fmt == "csv":
        out_path = out_dir / "bollette.csv"
        frame.to_csv(out_path, index=False)
        return out_path
    out_path = out_dir / "bollette.xlsx"
    frame.to_excel(out_path, index=False)
    return out_path


def html_page(body: str) -> bytes:
    page = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Estrattore Bollette</title>
  <style>
    :root {{
      --bg: #f5efe6;
      --panel: #fffdf9;
      --ink: #1f2937;
      --muted: #6b7280;
      --accent: #0f766e;
      --accent-2: #d97706;
      --line: #e7ddcf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Iowan Old Style", serif;
      background:
        radial-gradient(circle at top left, rgba(217,119,6,.14), transparent 28%),
        radial-gradient(circle at top right, rgba(15,118,110,.12), transparent 30%),
        linear-gradient(180deg, #faf6ef 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    .hero {{
      display: grid;
      gap: 18px;
      margin-bottom: 26px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(2rem, 4vw, 3.8rem);
      line-height: .95;
      letter-spacing: -.04em;
    }}
    .lede {{
      max-width: 760px;
      font-size: 1.05rem;
      color: var(--muted);
      line-height: 1.55;
    }}
    .card {{
      background: rgba(255,253,249,.92);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 18px 45px rgba(31,41,55,.06);
      padding: 24px;
      backdrop-filter: blur(8px);
    }}
    form {{
      display: grid;
      gap: 16px;
    }}
    .upload {{
      border: 2px dashed #cbbca8;
      border-radius: 18px;
      padding: 24px;
      background: linear-gradient(180deg, rgba(255,255,255,.82), rgba(255,248,239,.92));
    }}
    input[type=file] {{
      width: 100%;
      font-size: 1rem;
    }}
    .row {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      background: linear-gradient(135deg, var(--accent), #115e59);
      color: white;
      font-size: .98rem;
      cursor: pointer;
    }}
    .pill {{
      display: inline-flex;
      border-radius: 999px;
      padding: 8px 12px;
      background: #f6ead7;
      color: #8a4b08;
      font-size: .92rem;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 18px;
      font-size: .92rem;
      background: white;
      border-radius: 14px;
      overflow: hidden;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #efe5d8;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #f9f2e8;
      font-size: .8rem;
      text-transform: uppercase;
      letter-spacing: .05em;
      color: #7a6a57;
    }}
    .downloads {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 18px;
    }}
    .downloads a {{
      text-decoration: none;
      color: white;
      background: linear-gradient(135deg, var(--accent-2), #b45309);
      border-radius: 999px;
      padding: 10px 14px;
    }}
    .muted {{ color: var(--muted); }}
    .stack > * + * {{ margin-top: 16px; }}
    code {{ background: #f2ebe1; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <div class="wrap">{body}</div>
</body>
</html>"""
    return page.encode("utf-8")


def render_index(message: str = "") -> bytes:
    message_html = f'<div class="pill">{html.escape(message)}</div>' if message else ""
    body = f"""
    <section class="hero">
      <h1>Estrattore Bollette PDF</h1>
      <div class="lede">Carica una o piu' bollette in PDF. La webapp riconosce il template del fornitore, estrae i campi principali e genera un unico Excel con una riga per bolletta.</div>
      {message_html}
    </section>
    <section class="card">
      <form method="post" action="/upload" enctype="multipart/form-data">
        <div class="upload stack">
          <strong>Seleziona i PDF</strong>
          <div class="muted">Supporta upload multiplo. Al momento i template piu' robusti sono Acea e Octopus, con fallback generico sugli altri formati.</div>
          <input type="file" name="files" accept=".pdf,application/pdf" multiple required>
        </div>
        <div class="row">
          <button type="submit">Elabora e genera Excel</button>
          <span class="pill">Output: XLSX unico + CSV opzionale</span>
        </div>
      </form>
    </section>
    """
    return html_page(body)


def render_results(records: list[dict[str, str]], xlsx_path: Path, csv_path: Path) -> bytes:
    headers = [
        "source_file",
        "supplier_template",
        "invoice_date",
        "billing_period_start",
        "billing_period_end",
        "consumption_kwh",
        "total_amount_eur",
        "notes",
    ]
    rows_html = []
    for row in records:
        cells = "".join(f"<td>{html.escape(str(row.get(col, '') or ''))}</td>" for col in headers)
        rows_html.append(f"<tr>{cells}</tr>")
    table_html = "".join(rows_html)
    body = f"""
    <section class="hero">
      <h1>Elaborazione completata</h1>
      <div class="lede">Sono state elaborate {len(records)} bollette. Qui sotto trovi l'anteprima tabellare e i link ai file generati.</div>
    </section>
    <section class="card stack">
      <div class="downloads">
        <a href="/download?path={urllib.parse.quote(str(xlsx_path))}">Scarica Excel</a>
        <a href="/download?path={urllib.parse.quote(str(csv_path))}">Scarica CSV</a>
        <a href="/">Nuovo caricamento</a>
      </div>
      <table>
        <thead><tr>{"".join(f"<th>{html.escape(col)}</th>" for col in headers)}</tr></thead>
        <tbody>{table_html}</tbody>
      </table>
    </section>
    """
    return html_page(body)


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.respond(HTTPStatus.OK, render_index(), "text/html; charset=utf-8")
            return
        if parsed.path == "/download":
            query = urllib.parse.parse_qs(parsed.query)
            raw_path = query.get("path", [""])[0]
            path = Path(raw_path)
            try:
                resolved = path.resolve(strict=True)
            except FileNotFoundError:
                self.respond(HTTPStatus.NOT_FOUND, b"File non trovato", "text/plain; charset=utf-8")
                return
            if EXPORTS_DIR.resolve() not in resolved.parents:
                self.respond(HTTPStatus.FORBIDDEN, b"Percorso non consentito", "text/plain; charset=utf-8")
                return
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if resolved.suffix.lower() == ".csv":
                content_type = "text/csv; charset=utf-8"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(resolved.stat().st_size))
            self.send_header("Content-Disposition", f'attachment; filename="{resolved.name}"')
            self.end_headers()
            with resolved.open("rb") as handle:
                shutil.copyfileobj(handle, self.wfile)
            return
        self.respond(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        if self.path != "/upload":
            self.respond(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")
            return
        try:
            form = parse_multipart(self)
            files = form.get("files", [])
            if not files:
                self.respond(HTTPStatus.BAD_REQUEST, render_index("Nessun file selezionato."), "text/html; charset=utf-8")
                return
            saved_files = save_uploaded_files(files)  # type: ignore[arg-type]
            records = [asdict(build_record(path)) for path in saved_files]
            xlsx_path = export_records(records, "xlsx")
            csv_path = export_records(records, "csv")
            self.respond(HTTPStatus.OK, render_results(records, xlsx_path, csv_path), "text/html; charset=utf-8")
        except Exception as exc:  # pragma: no cover - defensive surface for web app
            message = f"Errore durante l'elaborazione: {exc}"
            self.respond(HTTPStatus.INTERNAL_SERVER_ERROR, render_index(message), "text/html; charset=utf-8")

    def log_message(self, format: str, *args: object) -> None:
        return

    def respond(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Webapp locale per estrazione bollette PDF.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host di ascolto (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Porta di ascolto (default: {DEFAULT_PORT})")
    args = parser.parse_args()
    ensure_dirs()
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"Webapp pronta su http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
