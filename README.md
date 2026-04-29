# Estrattore bollette luce e gas PDF -> XLSX

Questo progetto contiene un tool rule-based che:

- legge bollette elettriche e gas in PDF
- estrae i dati più rilevanti per ciascun servizio
- normalizza i valori principali (date, importi, consumi)
- genera un file `.xlsx` con un foglio per l'elettricità e uno per il gas
- sceglie automaticamente un template di parsing in base al fornitore riconosciuto

## Architettura

Il codice è suddiviso nel package `bollette/` con struttura simmetrica per i due servizi:

```
bollette/
├── models.py               # costanti ELECTRICITY_SERVICE_TYPE / GAS_SERVICE_TYPE
├── extractors.py           # primitivi condivisi (estrazione testo PDF, label matching)
├── discovery.py            # classify_pdf, discover_pdfs, group_pdfs_by_service
├── exporters.py            # export_xlsx (unico file, multi-foglio)
├── output_config.py        # OutputColumn, load_output_config
├── electricity/
│   ├── models.py           # BillRecord, OUTPUT_COLUMNS, NUMERIC_COLUMNS
│   ├── constants.py        # etichette luce (MONEY_LABELS, TEXT_LABELS, PERIOD_LABELS)
│   ├── extractors.py       # find_period, find_consumption, infer_supplier, ...
│   ├── builder.py          # build_record(pdf_path) -> BillRecord
│   └── templates/          # generic, octopus, acea, enel, iren, sen, edison
└── gas/
    ├── models.py           # GasBillRecord, GAS_OUTPUT_COLUMNS, GAS_NUMERIC_COLUMNS
    ├── extractors.py       # infer_gas_supplier_template
    ├── builder.py          # build_gas_record(pdf_path) -> GasBillRecord
    └── templates/          # generic_gas, dolomiti_gas
```

## Template supportati

### Elettricità
- `generic`: fallback per bollette non ancora mappate
- `octopus`: Octopus Energy
- `acea_standard`: Acea bollette periodiche standard
- `acea_conguaglio`: Acea con conguaglio/ricalcoli
- `enel`: Enel Energia
- `iren`: Iren Mercato
- `sen`: Servizio Elettrico Nazionale
- `edison`: Edison Energia

### Gas
- `generic_gas`: fallback per bollette gas non mappate
- `dolomiti_gas`: Dolomiti Energia Gas

Il template scelto viene scritto nella colonna `supplier_template`.

## Cosa estrae

### Elettricità (foglio "Elettricità")

- `source_file`, `supplier_template`, `supplier_name`
- `invoice_number`, `invoice_date`, `due_date`
- `customer_name`, `supply_address`, `pod_code`, `tariff_code`
- `billing_period_start`, `billing_period_end`
- `consumption_kwh`, `consumption_f1_kwh`, `consumption_f2_kwh`, `consumption_f3_kwh`
- `committed_power_kw`, `available_power_kw`
- `total_amount_eur`, `invoice_total_eur`, `bonus_eur`
- `energy_cost_eur`, `transport_eur`, `system_charges_eur`, `taxes_eur`, `vat_eur`, `tv_license_eur`
- tripletta `qty` / `unit_rate` / `imponibile_eur` per: `energy`, `losses`, `dispbt`, `commercialization`, `capacity_market`, `dispatching`, `transport_energy`, `transport_fixed`, `transport_power`, `uc3`, `uc6_fixed`, `uc6_variable`, `arim`, `asos`, `excise`
- `notes`

### Gas (foglio "Gas")

- `source_file`, `supplier_template`, `supplier_name`
- `invoice_number`, `invoice_date`, `due_date`
- `customer_name`, `supply_address`, `pdr_code`, `offer_name`
- `billing_period_start`, `billing_period_end`
- `consumption_smc`, `estimated_consumption_smc`, `annual_consumption_smc`
- `reading_start`, `reading_end`, `meter_serial`
- `gas_type`, `calorific_value`, `conversion_factor`
- `total_amount_eur`, `invoice_total_eur`
- `fixed_fee_eur`, `transport_eur`, `system_charges_eur`, `excise_eur`, `vat_eur`
- tripletta `qty` / `unit_rate` / `imponibile_eur` per: `raw_consumption`, `network_fee`, `gas_distribution`
- `notes`

La colonna `notes` segnala i campi non trovati, utile quando cambiano layout o terminologia della bolletta.

## Requisiti

- `pypdf >= 4.0`
- `pandas >= 2.0`
- `openpyxl >= 3.1`
- `python-dateutil >= 2.9`

Su macOS con Homebrew, tkinter richiede:

```bash
brew install python-tk@3.14
```

## Installazione dipendenze

```bash
python3 -m venv .venv
source .venv/bin/activate   # su Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Esecuzione da riga di comando

Su un singolo PDF:

```bash
python3 bill_extractor.py ./mia_bolletta.pdf
```

Su una cartella intera di PDF:

```bash
python3 bill_extractor.py ./pdf_bollette -o output/bollette.xlsx
```

Se la cartella contiene sia bollette luce sia bollette gas, il CLI le riconosce automaticamente e produce un unico file con due fogli: **Elettricità** e **Gas**.

### Configurazione colonne output

Di default l'output contiene tutte le colonne del parser. Puoi passare un file JSON per scegliere sottoinsieme, ordine e titolo delle colonne:

```bash
python3 bill_extractor.py ./pdf_bollette \
  -o output/bollette.xlsx \
  -e output_columns.energy_summary.json \
  -g output_gas_summary.json
```

Formato del file:

```json
{
  "columns": [
    {"source": "source_file", "title": "File"},
    {"source": "invoice_date", "title": "Data fattura"},
    {"source": "consumption_kwh", "title": "Consumo kWh"},
    {"source": "total_amount_eur", "title": "Totale da pagare"}
  ]
}
```

Per i template gas aggiungi `"service_type": "gas"` e scegli colonne dal tracciato gas. `source` deve essere una delle colonne elencate nella sezione "Cosa estrae".

## GUI desktop

```bash
python3 gui_bollette.py
```

La GUI mostra due combo (una per elettricità, una per gas) con i template JSON presenti nella cartella di lancio. Selezionando uno o più PDF e confermando il salvataggio, produce un unico file `.xlsx` con i fogli corrispondenti ai servizi trovati.

## Come funziona

Il tool usa:

- estrazione testo dal PDF con `pypdf`
- riconoscimento fornitore per parole chiave → scelta del template
- label matching per estrarre valori da layout reali
- normalizzazione di date (`YYYY-MM-DD`), importi (euro con punto decimale) e consumi
- merge intelligente su file esistente: aggiorna le righe già presenti per `source_file`, aggiunge le nuove

## Limiti attuali

- Funziona su PDF testuali; su PDF scannerizzati serve una fase OCR.
- Alcuni fornitori usano etichette molto diverse: in quei casi il file viene prodotto con più campi vuoti.
- Versione rule-based: non usa modelli AI per layout molto anomali.
