from __future__ import annotations

from dataclasses import dataclass

from ..models import GAS_SERVICE_TYPE


GAS_OUTPUT_COLUMNS = [
    "source_file",
    "service_type",
    "supplier_template",
    "supplier_name",
    "invoice_number",
    "invoice_date",
    "due_date",
    "customer_name",
    "customer_code",
    "contract_account",
    "contract_code",
    "fiscal_code",
    "vat_number",
    "supply_address",
    "pdr_code",
    "tariff_code",
    "offer_code",
    "price_type",
    "economic_conditions_start",
    "economic_conditions_end",
    "contract_end",
    "billing_period_start",
    "billing_period_end",
    "consumption_smc",
    "estimated_consumption_smc",
    "actual_consumption_mc",
    "actual_consumption_smc",
    "billed_consumption_mc",
    "billed_consumption_smc",
    "annual_consumption_smc",
    "annual_expense_eur",
    "customer_type",
    "use_type",
    "meter_id",
    "meter_type",
    "meter_class",
    "remi_code",
    "reading_start_date",
    "reading_end_date",
    "reading_start",
    "reading_end",
    "correction_coefficient",
    "calorific_value_gj_smc",
    "total_amount_eur",
    "invoice_total_eur",
    "gas_sales_eur",
    "gas_sales_variable_eur",
    "gas_sales_fixed_eur",
    "network_charges_eur",
    "network_variable_eur",
    "network_fixed_eur",
    "system_charges_eur",
    "taxes_eur",
    "excise_qty",
    "excise_unit_rate",
    "excise_eur",
    "vat_taxable_eur",
    "vat_eur",
    "raw_material_unit_rate",
    "spread_unit_rate",
    "fixed_fee_qty",
    "fixed_fee_unit_rate",
    "fixed_fee_imponibile_eur",
    "variable_fee_qty",
    "variable_fee_unit_rate",
    "variable_fee_imponibile_eur",
    "notes",
]

GAS_NUMERIC_COLUMNS = [
    "consumption_smc",
    "estimated_consumption_smc",
    "actual_consumption_mc",
    "actual_consumption_smc",
    "billed_consumption_mc",
    "billed_consumption_smc",
    "annual_consumption_smc",
    "annual_expense_eur",
    "reading_start",
    "reading_end",
    "correction_coefficient",
    "calorific_value_gj_smc",
    "total_amount_eur",
    "invoice_total_eur",
    "gas_sales_eur",
    "gas_sales_variable_eur",
    "gas_sales_fixed_eur",
    "network_charges_eur",
    "network_variable_eur",
    "network_fixed_eur",
    "system_charges_eur",
    "taxes_eur",
    "excise_qty",
    "excise_unit_rate",
    "excise_eur",
    "vat_taxable_eur",
    "vat_eur",
    "raw_material_unit_rate",
    "spread_unit_rate",
    "fixed_fee_qty",
    "fixed_fee_unit_rate",
    "fixed_fee_imponibile_eur",
    "variable_fee_qty",
    "variable_fee_unit_rate",
    "variable_fee_imponibile_eur",
]


@dataclass
class GasBillRecord:
    source_file: str
    service_type: str = GAS_SERVICE_TYPE
    supplier_template: str = ""
    supplier_name: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    due_date: str = ""
    customer_name: str = ""
    customer_code: str = ""
    contract_account: str = ""
    contract_code: str = ""
    fiscal_code: str = ""
    vat_number: str = ""
    supply_address: str = ""
    pdr_code: str = ""
    tariff_code: str = ""
    offer_code: str = ""
    price_type: str = ""
    economic_conditions_start: str = ""
    economic_conditions_end: str = ""
    contract_end: str = ""
    billing_period_start: str = ""
    billing_period_end: str = ""
    consumption_smc: str = ""
    estimated_consumption_smc: str = ""
    actual_consumption_mc: str = ""
    actual_consumption_smc: str = ""
    billed_consumption_mc: str = ""
    billed_consumption_smc: str = ""
    annual_consumption_smc: str = ""
    annual_expense_eur: str = ""
    customer_type: str = ""
    use_type: str = ""
    meter_id: str = ""
    meter_type: str = ""
    meter_class: str = ""
    remi_code: str = ""
    reading_start_date: str = ""
    reading_end_date: str = ""
    reading_start: str = ""
    reading_end: str = ""
    correction_coefficient: str = ""
    calorific_value_gj_smc: str = ""
    total_amount_eur: str = ""
    invoice_total_eur: str = ""
    gas_sales_eur: str = ""
    gas_sales_variable_eur: str = ""
    gas_sales_fixed_eur: str = ""
    network_charges_eur: str = ""
    network_variable_eur: str = ""
    network_fixed_eur: str = ""
    system_charges_eur: str = ""
    taxes_eur: str = ""
    excise_qty: str = ""
    excise_unit_rate: str = ""
    excise_eur: str = ""
    vat_taxable_eur: str = ""
    vat_eur: str = ""
    raw_material_unit_rate: str = ""
    spread_unit_rate: str = ""
    fixed_fee_qty: str = ""
    fixed_fee_unit_rate: str = ""
    fixed_fee_imponibile_eur: str = ""
    variable_fee_qty: str = ""
    variable_fee_unit_rate: str = ""
    variable_fee_imponibile_eur: str = ""
    notes: str = ""
