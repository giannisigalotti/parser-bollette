from __future__ import annotations

import re

from ..models import GasBillRecord
from ...text_utils import normalize_unit_rate, parse_date, parse_decimal, parse_float_num
from .base import build_generic_gas_regex_overrides


def build_dolomiti_gas_overrides(raw_text: str, lines: list[str]) -> dict[str, str]:
    overrides = build_generic_gas_regex_overrides(raw_text, lines)
    overrides["supplier_name"] = "Dolomiti Energia Mercato SpA"

    customer = _line_after(lines, "I TUOI DATI IDENTIFICATIVI")
    if customer:
        overrides["customer_name"] = customer

    supply_address = _extract_inline_value(lines, "Indirizzo di fornitura:")
    if supply_address:
        overrides["supply_address"] = supply_address

    pdr = _extract_inline_value(lines, "Codice PDR:")
    if pdr:
        overrides["pdr_code"] = pdr

    for label, field in [
        ("Codice cliente:", "customer_code"),
        ("Conto contrattuale:", "contract_account"),
        ("Contratto:", "contract_code"),
        ("Codice Fiscale:", "fiscal_code"),
        ("Partita IVA:", "vat_number"),
        ("Codice offerta:", "offer_code"),
        ("Tipologia di prezzo:", "price_type"),
        ("Tipologia di cliente:", "customer_type"),
        ("Tipologia d'uso:", "use_type"),
    ]:
        value = _extract_inline_value(lines, label)
        if value:
            overrides[field] = value

    for label, field in [
        ("Data di decorrenza condizioni economiche:", "economic_conditions_start"),
        ("Data di scadenza condizioni economiche:", "economic_conditions_end"),
        ("Data di scadenza contratto:", "contract_end"),
    ]:
        value = _extract_inline_value(lines, label)
        if value:
            overrides[field] = parse_date(value)

    annual = re.search(r"CONSUMO ANNUO mc\s+([0-9.]+)", raw_text, re.IGNORECASE)
    if annual:
        overrides["annual_consumption_smc"] = parse_decimal(annual.group(1))

    annual_expense = re.search(r"SPESA ANNUA SOSTENUTA\s+([0-9.,]+)\s*€", raw_text, re.IGNORECASE)
    if annual_expense:
        overrides["annual_expense_eur"] = parse_decimal(annual_expense.group(1))

    for label, field in [
        ("Classe misuratore:", "meter_class"),
        ("Codice REMI:", "remi_code"),
    ]:
        value = _extract_inline_value(lines, label)
        if value:
            overrides[field] = value

    for label, field in [
        ("Coefficiente correttivo (C):", "correction_coefficient"),
        ("Potere calorifico superiore convenzionale (P):", "calorific_value_gj_smc"),
    ]:
        value = _extract_inline_value(lines, label)
        if value:
            parsed = parse_decimal(value)
            overrides[field] = parsed or value

    readings = _extract_readings(raw_text)
    overrides.update(readings)

    consumptions = _extract_meter_consumptions(raw_text)
    overrides.update(consumptions)

    formula = _extract_formula_values(raw_text)
    overrides.update(formula)

    system = re.search(r"totale oneri generali di sistema\s+([0-9.,]+)", raw_text, re.IGNORECASE)
    if system:
        overrides["system_charges_eur"] = parse_decimal(system.group(1))

    sales_values = _sum_summary_amounts(raw_text, r"di cui spesa per vendita gas naturale")
    if sales_values:
        overrides["gas_sales_eur"] = sales_values

    network_values = _sum_summary_amounts(
        raw_text,
        r"di cui spesa per la rete e gli oneri generali di sistema",
    )
    if network_values:
        overrides["network_charges_eur"] = network_values
    network_variable = _summary_amount(raw_text, r"di cui spesa per la rete e gli oneri generali di sistema", occurrence=1)
    if network_variable:
        overrides["network_variable_eur"] = network_variable
    network_fixed = _summary_amount(raw_text, r"di cui spesa per la rete e gli oneri generali di sistema", occurrence=2)
    if network_fixed:
        overrides["network_fixed_eur"] = network_fixed

    sales_variable = _summary_amount(raw_text, r"di cui spesa per vendita gas naturale", occurrence=1)
    if sales_variable:
        overrides["gas_sales_variable_eur"] = sales_variable
    sales_fixed = _summary_amount(raw_text, r"di cui spesa per vendita gas naturale", occurrence=2)
    if sales_fixed:
        overrides["gas_sales_fixed_eur"] = sales_fixed

    taxes_section = _section(raw_text, r"IMPOSTE periodo", r"DETTAGLIO IVA")
    excise = _extract_excise(taxes_section)
    overrides.update(excise)

    vat = _extract_vat(raw_text)
    overrides.update(vat)

    fixed = _extract_summary_row(raw_text, r"QUOTA FISSA")
    if fixed:
        overrides["fixed_fee_qty"], overrides["fixed_fee_unit_rate"], overrides["fixed_fee_imponibile_eur"] = fixed

    variable = _extract_summary_row(raw_text, r"QUOTA PER CONSUMI")
    if variable:
        overrides["variable_fee_qty"], overrides["variable_fee_unit_rate"], overrides["variable_fee_imponibile_eur"] = variable

    return overrides


def apply_dolomiti_gas_template(record: GasBillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_dolomiti_gas_overrides(raw_text, lines).items():
        setattr(record, field, value)


def _line_after(lines: list[str], label: str) -> str:
    for idx, line in enumerate(lines):
        if line == label and idx + 1 < len(lines):
            return lines[idx + 1]
    return ""


def _extract_inline_value(lines: list[str], label: str) -> str:
    for line in lines:
        if line.lower().startswith(label.lower()):
            return line[len(label):].strip()
    return ""


def _extract_summary_row(raw_text: str, label: str) -> tuple[str, str, str] | None:
    match = re.search(
        label + r"\s*\n\s*([0-9.,]+)\s*(Smc|mesi)\s+([0-9.,]+)\s*(€/\w+)\s+([0-9.,]+)",
        raw_text,
        re.IGNORECASE,
    )
    if not match:
        return None
    qty = parse_decimal(match.group(1))
    unit_rate = parse_float_num(match.group(3))
    amount = parse_decimal(match.group(5))
    unit = match.group(4)
    return (
        qty,
        normalize_unit_rate(unit_rate, unit) if unit_rate is not None else "",
        amount,
    )


def _summary_amount(raw_text: str, label: str, occurrence: int) -> str:
    matches = list(
        re.finditer(label + r"\s+[0-9.,]+\s*€/[A-Za-z]+\s+([0-9.,]+)", raw_text, re.IGNORECASE)
    )
    if len(matches) < occurrence:
        return ""
    return parse_decimal(matches[occurrence - 1].group(1))


def _sum_summary_amounts(raw_text: str, label: str) -> str:
    values = [
        parse_decimal(match.group(1))
        for match in re.finditer(label + r"\s+[0-9.,]+\s*€/[A-Za-z]+\s+([0-9.,]+)", raw_text, re.IGNORECASE)
    ]
    total = sum(float(v) for v in values if v)
    return f"{total:.2f}" if values else ""


def _section(raw_text: str, start_label: str, end_label: str) -> str:
    start = re.search(start_label, raw_text, re.IGNORECASE)
    if not start:
        return ""
    tail = raw_text[start.end():]
    end = re.search(end_label, tail, re.IGNORECASE)
    return tail[: end.start()] if end else tail


def _extract_readings(raw_text: str) -> dict[str, str]:
    overrides: dict[str, str] = {}
    meter = re.search(r"LETTURE contatore:\s*([0-9]+)\s+([^\n]+)", raw_text, re.IGNORECASE)
    if meter:
        overrides["meter_id"] = meter.group(1)
        overrides["meter_type"] = meter.group(2).strip(" -")

    readings = re.search(
        r"UM\s+([0-9]{2}/[0-9]{2}/[0-9]{4})\s+([0-9]{2}/[0-9]{2}/[0-9]{4}).*?"
        r"Smc\s+([0-9.]+)\s+([0-9.]+)",
        raw_text,
        re.IGNORECASE | re.DOTALL,
    )
    if readings:
        overrides["reading_start_date"] = parse_date(readings.group(1))
        overrides["reading_end_date"] = parse_date(readings.group(2))
        overrides["reading_start"] = parse_decimal(readings.group(3))
        overrides["reading_end"] = parse_decimal(readings.group(4))
    return overrides


def _extract_meter_consumptions(raw_text: str) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for label, prefix in [("EFFETTIVI", "actual"), ("FATTURATI", "billed")]:
        match = re.search(
            label + r"\s+([0-9.,]+)\s+([0-9.,]+)\s+([0-9/]+-[0-9/]+)",
            raw_text,
            re.IGNORECASE,
        )
        if not match:
            continue
        overrides[f"{prefix}_consumption_mc"] = parse_decimal(match.group(1))
        overrides[f"{prefix}_consumption_smc"] = parse_decimal(match.group(2))
    return overrides


def _extract_formula_values(raw_text: str) -> dict[str, str]:
    overrides: dict[str, str] = {}
    raw_material = re.search(r"MATERIA PRIMA GAS\s+([0-9.,]+)", raw_text, re.IGNORECASE)
    if raw_material:
        parsed = parse_float_num(raw_material.group(1))
        overrides["raw_material_unit_rate"] = normalize_unit_rate(parsed, "€/Smc") if parsed is not None else ""
    spread = re.search(r"SPREAD\s+([0-9.,]+)", raw_text, re.IGNORECASE)
    if spread:
        parsed = parse_float_num(spread.group(1))
        overrides["spread_unit_rate"] = normalize_unit_rate(parsed, "€/Smc") if parsed is not None else ""
    return overrides


def _extract_excise(taxes_section: str) -> dict[str, str]:
    rows: list[tuple[float, float, float]] = []
    for match in re.finditer(
        r"accisa uso domestico[^\n]+?€/Smc\s+([0-9.,]+)\s+([0-9.,]+)\s+([0-9.,]+)\s*$",
        taxes_section,
        re.IGNORECASE | re.MULTILINE,
    ):
        rate = parse_float_num(match.group(1))
        qty = parse_float_num(match.group(2))
        amount = parse_float_num(match.group(3))
        if rate is None or qty is None or amount is None:
            continue
        rows.append((rate, qty, amount))
    if not rows:
        return {}
    qty_total = sum(qty for _rate, qty, _amount in rows)
    amount_total = sum(amount for _rate, _qty, amount in rows)
    weighted_rate = sum(rate * qty for rate, qty, _amount in rows) / qty_total if qty_total else 0
    return {
        "excise_qty": f"{qty_total:.2f}",
        "excise_unit_rate": normalize_unit_rate(weighted_rate, "€/Smc") if qty_total else "",
        "excise_eur": f"{amount_total:.2f}",
    }


def _extract_vat(raw_text: str) -> dict[str, str]:
    rows = [
        (parse_decimal(match.group(1)), parse_decimal(match.group(2)))
        for match in re.finditer(r"\b\d+\s+-\s+Iva\s+\d+%\s+([0-9.,]+)\s+([0-9.,]+)", raw_text, re.IGNORECASE)
    ]
    taxable = next((taxable for taxable, amount in reversed(rows) if amount and float(amount) != 0), "")
    total = re.search(r"TOTALE IVA\s+([0-9.,]+)", raw_text, re.IGNORECASE)
    return {
        "vat_taxable_eur": taxable,
        "vat_eur": parse_decimal(total.group(1)) if total else "",
    }
