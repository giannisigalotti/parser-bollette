"""Label tables used by electricity extractors and templates."""

MONEY_LABELS: dict[str, list[str]] = {
    "total_amount_eur": [
        "totale da pagare",
        "totale bolletta",
        "importo da pagare",
        "totale fattura",
        "totale documento",
    ],
    "taxes_eur": ["imposte", "accise"],
    "vat_eur": ["iva"],
    "transport_eur": ["spesa per il trasporto", "trasporto e gestione del contatore"],
    "system_charges_eur": ["spesa per oneri di sistema", "oneri di sistema"],
    "energy_cost_eur": ["spesa per la materia energia", "costo energia", "corrispettivo energia"],
    "tv_license_eur": ["canone rai", "canone tv"],
}

TEXT_LABELS: dict[str, list[str]] = {
    "supplier_name": ["venditore", "fornitore", "societa di vendita", "emittente"],
    "invoice_number": ["numero fattura", "n. fattura", "fattura n", "numero documento"],
    "invoice_date": ["data emissione", "data fattura", "emessa il"],
    "due_date": ["scadenza", "data scadenza"],
    "customer_name": ["intestatario", "cliente", "ragione sociale", "nominativo"],
    "supply_address": ["indirizzo di fornitura", "presso fornitura", "ubicazione fornitura"],
    "tariff_code": ["offerta", "tipologia offerta", "tariffa", "codice offerta"],
    "pod_code": ["pod"],
}

PERIOD_LABELS: list[str] = [
    "periodo",
    "periodo di riferimento",
    "consumi dal",
    "periodo fatturato",
]
