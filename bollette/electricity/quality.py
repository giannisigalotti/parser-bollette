from __future__ import annotations

from datetime import date, timedelta

from ..text_utils import parse_float_num
from .models import BillRecord


MISSING_CHECK_EXCLUDED_FIELDS = {"source_file", "confidence", "confidence_notes", "notes"}
TEXT_FIELDS = {
    "source_file",
    "confidence_notes",
    "supplier_template",
    "supplier_name",
    "invoice_number",
    "customer_name",
    "supply_address",
    "pod_code",
    "tariff_code",
    "notes",
}
DATE_FIELDS = {"invoice_date", "due_date", "billing_period_start", "billing_period_end"}
NUMERIC_RANGES = {
    "confidence": (0, 100),
    "consumption_kwh": (0, 10_000_000),
    "consumption_f1_kwh": (0, 10_000_000),
    "consumption_f2_kwh": (0, 10_000_000),
    "consumption_f3_kwh": (0, 10_000_000),
    "reactive_energy_kvarh": (0, 10_000_000),
    "reactive_energy_f1_kvarh": (0, 10_000_000),
    "reactive_energy_f2_kvarh": (0, 10_000_000),
    "reactive_energy_f3_kvarh": (0, 10_000_000),
    "committed_power_kw": (0, 10_000),
    "available_power_kw": (0, 10_000),
    "total_amount_eur": (-1_000_000, 10_000_000),
    "invoice_total_eur": (-1_000_000, 10_000_000),
    "bonus_eur": (-1_000_000, 1_000_000),
    "energy_cost_eur": (-1_000_000, 10_000_000),
    "transport_eur": (-1_000_000, 10_000_000),
    "system_charges_eur": (-1_000_000, 10_000_000),
    "taxes_eur": (-1_000_000, 10_000_000),
    "vat_eur": (-1_000_000, 10_000_000),
    "tv_license_eur": (-1_000_000, 10_000_000),
}


def compute_confidence(record: BillRecord, raw_text: str) -> str:
    score, _reasons = compute_confidence_details(record, raw_text)
    return str(score)


def compute_confidence_details(record: BillRecord, raw_text: str) -> tuple[int, list[str]]:
    score = 100
    reasons: list[str] = []

    required_weights = {
        "supplier_template": 8,
        "supplier_name": 4,
        "invoice_number": 5,
        "invoice_date": 6,
        "customer_name": 6,
        "pod_code": 8,
        "billing_period_start": 7,
        "billing_period_end": 7,
        "consumption_kwh": 10,
        "invoice_total_eur": 6,
    }
    for field, weight in required_weights.items():
        if not getattr(record, field):
            score -= weight
            reasons.append(f"{field} mancante")

    if not record.supply_address:
        score -= 3
        reasons.append("supply_address mancante")
    if not record.tariff_code:
        score -= 2
        reasons.append("tariff_code mancante")
    if record.supplier_template in {"", "generic"}:
        score -= 8
        reasons.append("template fornitore generico o non riconosciuto")

    for penalty, reason in (
        _consumption_penalty(record),
        _reactive_penalty(record, raw_text),
        _period_penalty(record),
        _amount_penalty(record),
    ):
        if penalty:
            score -= penalty
            reasons.append(reason)

    return max(0, min(100, round(score))), reasons


def refine_confidence_for_output(
    record: BillRecord,
    selected_fields: list[str],
    optional_fields: set[str] | None = None,
) -> str:
    score, _notes = refine_quality_for_output(record, selected_fields, optional_fields)
    return str(score)


def refine_quality_for_output(
    record: BillRecord,
    selected_fields: list[str],
    optional_fields: set[str] | None = None,
) -> tuple[int, str]:
    optional_fields = optional_fields or set()
    score = _num(record.confidence)
    if score is None:
        score = float(compute_confidence(record, ""))
    reasons = _split_reasons(record.confidence_notes)

    selected = [
        field
        for field in selected_fields
        if field not in MISSING_CHECK_EXCLUDED_FIELDS and field not in optional_fields
    ]
    selected_missing = [field for field in selected if not getattr(record, field, "")]
    if selected_missing:
        score -= min(30, len(selected_missing) * 4)
        reasons.append("campi del template output mancanti: " + ", ".join(selected_missing))

    note_alerts = _selected_note_alerts(record.notes, selected_fields, optional_fields)
    if note_alerts:
        score -= min(20, len(note_alerts) * 3)
        reasons.append("alert nelle note per colonne del template: " + ", ".join(note_alerts))

    type_errors, range_errors = _type_and_range_errors(record, selected_fields)
    if type_errors:
        score -= min(25, len(type_errors) * 5)
        reasons.append("tipo dato non valido: " + ", ".join(type_errors))
    if range_errors:
        score -= min(20, len(range_errors) * 4)
        reasons.append("valore fuori range atteso: " + ", ".join(range_errors))

    final_score = max(0, min(100, round(score)))
    return final_score, "ok" if final_score == 100 else "; ".join(dict.fromkeys(reasons))


def _consumption_penalty(record: BillRecord) -> tuple[int, str]:
    total = _num(record.consumption_kwh)
    bands = [
        _num(record.consumption_f1_kwh),
        _num(record.consumption_f2_kwh),
        _num(record.consumption_f3_kwh),
    ]
    if total is None:
        return 0, ""
    missing_bands = sum(value is None for value in bands)
    if missing_bands == 3:
        return 6, "fasce consumo F1/F2/F3 mancanti"
    if missing_bands:
        return missing_bands * 3, "una o piu' fasce consumo F1/F2/F3 mancanti"

    band_total = sum(value or 0 for value in bands)
    tolerance = max(1.0, total * 0.01)
    if abs(total - band_total) > tolerance:
        return 10, "totale consumo non coerente con somma F1/F2/F3"
    return 0, ""


def _reactive_penalty(record: BillRecord, raw_text: str) -> tuple[int, str]:
    if "reattiv" not in raw_text.lower():
        return 0, ""
    if record.reactive_energy_kvarh:
        return 0, ""
    if any(
        (
            record.reactive_energy_f1_kvarh,
            record.reactive_energy_f2_kvarh,
            record.reactive_energy_f3_kvarh,
        )
    ):
        return 3, "energia reattiva totale mancante ma presente per fascia"
    return 6, "energia reattiva indicata nel PDF ma non estratta"


def _period_penalty(record: BillRecord) -> tuple[int, str]:
    start = _date(record.billing_period_start)
    end = _date(record.billing_period_end)
    if start and end and start > end:
        return 8, "periodo fatturazione non coerente"
    return 0, ""


def _amount_penalty(record: BillRecord) -> tuple[int, str]:
    penalty = 0
    reasons: list[str] = []
    invoice_total = _num(record.invoice_total_eur)
    if invoice_total is not None and invoice_total <= 0:
        penalty += 4
        reasons.append("totale bolletta minore o uguale a zero")
    if not any((record.energy_cost_eur, record.transport_eur, record.vat_eur, record.taxes_eur)):
        penalty += 5
        reasons.append("componenti economiche principali mancanti")
    return penalty, "; ".join(reasons)


def _num(value: str) -> float | None:
    if value in {"", None}:  # type: ignore[comparison-overlap]
        return None
    return parse_float_num(str(value))


def _date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _selected_note_alerts(notes: str, selected_fields: list[str], optional_fields: set[str]) -> list[str]:
    if not notes:
        return []
    normalized_notes = notes.lower()
    return [
        field
        for field in selected_fields
        if field and field not in optional_fields and field.lower() in normalized_notes
    ]


def _type_and_range_errors(record: BillRecord, selected_fields: list[str]) -> tuple[list[str], list[str]]:
    type_errors: list[str] = []
    range_errors: list[str] = []
    min_date = date(1990, 1, 1)
    max_date = date.today() + timedelta(days=366)

    for field in selected_fields:
        if field in MISSING_CHECK_EXCLUDED_FIELDS:
            continue
        value = getattr(record, field, "")
        if value in {"", None}:  # type: ignore[comparison-overlap]
            continue

        if field in DATE_FIELDS:
            parsed = _date(str(value))
            if parsed is None:
                type_errors.append(field)
            elif parsed < min_date or parsed > max_date:
                range_errors.append(field)
        elif field in NUMERIC_RANGES or field.endswith(("_eur", "_kwh", "_kvarh", "_kw", "_qty", "_unit_rate")):
            parsed_num = _num(str(value))
            if parsed_num is None:
                type_errors.append(field)
                continue
            low, high = NUMERIC_RANGES.get(field, (-1_000_000_000, 1_000_000_000))
            if parsed_num < low or parsed_num > high:
                range_errors.append(field)
        elif field in TEXT_FIELDS and not str(value).strip():
            type_errors.append(field)

    start = _date(record.billing_period_start)
    end = _date(record.billing_period_end)
    if start and end:
        duration = (end - start).days + 1
        if duration <= 0 or duration > 400:
            range_errors.append("billing_period")

    return type_errors, range_errors


def _split_reasons(value: str) -> list[str]:
    if not value or value == "ok":
        return []
    return [part.strip() for part in value.split(";") if part.strip()]
