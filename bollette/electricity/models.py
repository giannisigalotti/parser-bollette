from __future__ import annotations

from dataclasses import dataclass


OUTPUT_COLUMNS = [
    "source_file",
    "supplier_template",
    "supplier_name",
    "invoice_number",
    "invoice_date",
    "due_date",
    "customer_name",
    "supply_address",
    "pod_code",
    "tariff_code",
    "billing_period_start",
    "billing_period_end",
    "consumption_kwh",
    "consumption_f1_kwh",
    "consumption_f2_kwh",
    "consumption_f3_kwh",
    "reactive_energy_kvarh",
    "reactive_energy_f1_kvarh",
    "reactive_energy_f2_kvarh",
    "reactive_energy_f3_kvarh",
    "committed_power_kw",
    "available_power_kw",
    "total_amount_eur",
    "invoice_total_eur",
    "bonus_eur",
    "energy_cost_eur",
    "transport_eur",
    "system_charges_eur",
    "taxes_eur",
    "vat_eur",
    "tv_license_eur",
    "energy_qty",
    "energy_unit_rate",
    "energy_imponibile_eur",
    "losses_qty",
    "losses_unit_rate",
    "losses_imponibile_eur",
    "dispbt_qty",
    "dispbt_unit_rate",
    "dispbt_imponibile_eur",
    "commercialization_qty",
    "commercialization_unit_rate",
    "commercialization_imponibile_eur",
    "capacity_market_qty",
    "capacity_market_unit_rate",
    "capacity_market_imponibile_eur",
    "dispatching_qty",
    "dispatching_unit_rate",
    "dispatching_imponibile_eur",
    "transport_energy_qty",
    "transport_energy_unit_rate",
    "transport_energy_imponibile_eur",
    "transport_fixed_qty",
    "transport_fixed_unit_rate",
    "transport_fixed_imponibile_eur",
    "transport_power_qty",
    "transport_power_unit_rate",
    "transport_power_imponibile_eur",
    "uc3_qty",
    "uc3_unit_rate",
    "uc3_imponibile_eur",
    "uc6_fixed_qty",
    "uc6_fixed_unit_rate",
    "uc6_fixed_imponibile_eur",
    "uc6_variable_qty",
    "uc6_variable_unit_rate",
    "uc6_variable_imponibile_eur",
    "arim_qty",
    "arim_unit_rate",
    "arim_imponibile_eur",
    "asos_qty",
    "asos_unit_rate",
    "asos_imponibile_eur",
    "excise_qty",
    "excise_unit_rate",
    "excise_imponibile_eur",
    "confidence",
    "confidence_notes",
    "notes",
]

NUMERIC_COLUMNS = [
    "confidence",
    "consumption_kwh",
    "consumption_f1_kwh",
    "consumption_f2_kwh",
    "consumption_f3_kwh",
    "reactive_energy_kvarh",
    "reactive_energy_f1_kvarh",
    "reactive_energy_f2_kvarh",
    "reactive_energy_f3_kvarh",
    "committed_power_kw",
    "available_power_kw",
    "total_amount_eur",
    "invoice_total_eur",
    "bonus_eur",
    "energy_cost_eur",
    "transport_eur",
    "system_charges_eur",
    "taxes_eur",
    "vat_eur",
    "tv_license_eur",
    "energy_qty",
    "energy_imponibile_eur",
    "energy_unit_rate",
    "losses_qty",
    "losses_imponibile_eur",
    "losses_unit_rate",
    "dispbt_qty",
    "dispbt_imponibile_eur",
    "dispbt_unit_rate",
    "commercialization_qty",
    "commercialization_imponibile_eur",
    "commercialization_unit_rate",
    "capacity_market_qty",
    "capacity_market_imponibile_eur",
    "capacity_market_unit_rate",
    "dispatching_qty",
    "dispatching_imponibile_eur",
    "dispatching_unit_rate",
    "transport_energy_qty",
    "transport_energy_imponibile_eur",
    "transport_energy_unit_rate",
    "transport_fixed_qty",
    "transport_fixed_imponibile_eur",
    "transport_fixed_unit_rate",
    "transport_power_qty",
    "transport_power_imponibile_eur",
    "transport_power_unit_rate",
    "uc3_qty",
    "uc3_imponibile_eur",
    "uc3_unit_rate",
    "uc6_fixed_qty",
    "uc6_fixed_imponibile_eur",
    "uc6_fixed_unit_rate",
    "uc6_variable_qty",
    "uc6_variable_imponibile_eur",
    "uc6_variable_unit_rate",
    "arim_qty",
    "arim_imponibile_eur",
    "arim_unit_rate",
    "asos_qty",
    "asos_imponibile_eur",
    "asos_unit_rate",
    "excise_qty",
    "excise_imponibile_eur",
    "excise_unit_rate",
]


@dataclass
class BillRecord:
    source_file: str
    supplier_template: str = ""
    supplier_name: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    due_date: str = ""
    customer_name: str = ""
    supply_address: str = ""
    pod_code: str = ""
    tariff_code: str = ""
    billing_period_start: str = ""
    billing_period_end: str = ""
    consumption_kwh: str = ""
    consumption_f1_kwh: str = ""
    consumption_f2_kwh: str = ""
    consumption_f3_kwh: str = ""
    reactive_energy_kvarh: str = ""
    reactive_energy_f1_kvarh: str = ""
    reactive_energy_f2_kvarh: str = ""
    reactive_energy_f3_kvarh: str = ""
    committed_power_kw: str = ""
    available_power_kw: str = ""
    total_amount_eur: str = ""
    invoice_total_eur: str = ""
    bonus_eur: str = ""
    energy_cost_eur: str = ""
    transport_eur: str = ""
    system_charges_eur: str = ""
    taxes_eur: str = ""
    vat_eur: str = ""
    tv_license_eur: str = ""
    energy_qty: str = ""
    energy_unit_rate: str = ""
    energy_imponibile_eur: str = ""
    losses_qty: str = ""
    losses_unit_rate: str = ""
    losses_imponibile_eur: str = ""
    dispbt_qty: str = ""
    dispbt_unit_rate: str = ""
    dispbt_imponibile_eur: str = ""
    commercialization_qty: str = ""
    commercialization_unit_rate: str = ""
    commercialization_imponibile_eur: str = ""
    capacity_market_qty: str = ""
    capacity_market_unit_rate: str = ""
    capacity_market_imponibile_eur: str = ""
    dispatching_qty: str = ""
    dispatching_unit_rate: str = ""
    dispatching_imponibile_eur: str = ""
    transport_energy_qty: str = ""
    transport_energy_unit_rate: str = ""
    transport_energy_imponibile_eur: str = ""
    transport_fixed_qty: str = ""
    transport_fixed_unit_rate: str = ""
    transport_fixed_imponibile_eur: str = ""
    transport_power_qty: str = ""
    transport_power_unit_rate: str = ""
    transport_power_imponibile_eur: str = ""
    uc3_qty: str = ""
    uc3_unit_rate: str = ""
    uc3_imponibile_eur: str = ""
    uc6_fixed_qty: str = ""
    uc6_fixed_unit_rate: str = ""
    uc6_fixed_imponibile_eur: str = ""
    uc6_variable_qty: str = ""
    uc6_variable_unit_rate: str = ""
    uc6_variable_imponibile_eur: str = ""
    arim_qty: str = ""
    arim_unit_rate: str = ""
    arim_imponibile_eur: str = ""
    asos_qty: str = ""
    asos_unit_rate: str = ""
    asos_imponibile_eur: str = ""
    excise_qty: str = ""
    excise_unit_rate: str = ""
    excise_imponibile_eur: str = ""
    confidence: str = ""
    confidence_notes: str = ""
    notes: str = ""
