# Estrattore bollette luce PDF -> CSV/XLSX

Questo progetto contiene una prima versione semplice ma gia' utilizzabile di un tool che:

- legge una bolletta elettrica in PDF
- estrae i dati piu' rilevanti
- normalizza i valori principali
- genera un file `csv` o `xlsx` con una riga per ogni bolletta
- sceglie automaticamente un template di parsing in base al fornitore riconosciuto

## Cosa estrae

Le colonne attuali sono:

- `source_file`
- `supplier_template`
- `supplier_name`
- `invoice_number`
- `invoice_date`
- `due_date`
- `customer_name`
- `supply_address`
- `pod_code`
- `tariff_code`
- `billing_period_start`
- `billing_period_end`
- `consumption_kwh`
- `consumption_f1_kwh`
- `consumption_f2_kwh`
- `consumption_f3_kwh`
- `committed_power_kw`
- `total_amount_eur`
- `invoice_total_eur`
- `bonus_eur`
- `energy_cost_eur`
- `transport_eur`
- `system_charges_eur`
- `taxes_eur`
- `vat_eur`
- `tv_license_eur`
- tripletta `qty` / `unit_rate` / `imponibile_eur` per:
- `energy`
- `losses`
- `dispbt`
- `commercialization`
- `capacity_market`
- `dispatching`
- `transport_energy`
- `transport_fixed`
- `transport_power`
- `uc3`
- `uc6_fixed`
- `uc6_variable`
- `arim`
- `asos`
- `excise`
- `notes`

La colonna `notes` segnala i campi non trovati, utile quando cambiano layout o terminologia della bolletta.
In alcuni formati alcune voci non sono separabili in modo pulito, quindi possono restare vuote anche se il totale bolletta e' corretto.

## Architettura template

Il parser ora lavora con una logica a template:

- `generic`: fallback comune per bollette non ancora mappate in dettaglio
- `octopus`: template dedicato a Octopus Energy, gia' tarato sul PDF reale fornito
- `acea_standard`: template dedicato alle bollette Acea periodiche standard
- `acea_conguaglio`: template dedicato alle bollette Acea con conguaglio/ricalcoli

Il template scelto viene scritto nella colonna `supplier_template`.

Per le bollette `acea_conguaglio`, lo script privilegia i campi riepilogativi affidabili e lascia vuoti i dettagli componente quando le tabelle mischiano periodi storici, restituzioni acconti o ricalcoli che renderebbero fuorviante una somma diretta.

## Requisiti

Dipendenze Python necessarie:

- `pypdf >= 4.0`
- `pandas >= 2.0`
- `openpyxl >= 3.1`
- `python-dateutil >= 2.9`

Su macOS con Homebrew, tkinter richiede un pacchetto aggiuntivo:

```bash
brew install python-tk@3.14
```

## Installazione dipendenze

```bash
pip install -r requirements.txt
```

Consigliato: usa un virtual environment per isolare le dipendenze.

```bash
python3 -m venv .venv
source .venv/bin/activate   # su Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Esecuzione da riga di comando

Su un singolo PDF:

```bash
python3 bill_extractor.py ./mia_bolletta.pdf -o output/bolletta.csv
```

Su una cartella intera di PDF:

```bash
python3 bill_extractor.py ./pdf_bollette -o output/bollette.xlsx
```

L'output Excel/CSV contiene una riga per ogni PDF trovato nella cartella.

## GUI desktop

```bash
python3 gui_bollette.py
```

## Webapp locale

E' disponibile anche una piccola webapp locale con upload multiplo PDF, anteprima risultati e download di Excel/CSV.

```bash
python3 webapp.py
```

Con porta personalizzata:

```bash
python3 webapp.py --port 8080
```

Poi apri `http://127.0.0.1:8765` nel browser.

## Distribuzione come eseguibile (PyInstaller)

E' possibile compilare il progetto in un eseguibile autonomo che non richiede Python installato sulla macchina dell'utente finale.

### Prerequisiti build

```bash
pip install -r requirements-dev.txt
```

### Compilazione

```bash
# GUI + CLI insieme
python3 build.py

# Solo GUI
python3 build.py --gui

# Solo CLI
python3 build.py --cli
```

### Artefatti prodotti in `dist/`

| Piattaforma | GUI | CLI |
|---|---|---|
| macOS | `EstrattoreBollette.app` | `bollette-cli` |
| Windows | `EstrattoreBollette.exe` | `bollette-cli.exe` |
| Linux | `EstrattoreBollette` | `bollette-cli` |

Su macOS il bundle `.app` puo' essere trascinato direttamente in `/Applications`.

### Build multipiattaforma

PyInstaller deve girare **sul sistema operativo target**: per produrre i binari per Mac, Windows e Linux occorre eseguire `python3 build.py` su ciascuna delle tre piattaforme. E' possibile automatizzare il processo con una pipeline CI/CD (ad esempio GitHub Actions) se si vuole distribuire a piu' utenti.

## Come funziona

Il tool usa una combinazione di:

- estrazione testo dal PDF
- riconoscimento per etichette comuni nelle bollette italiane
- normalizzazione di date in formato `YYYY-MM-DD`
- normalizzazione importi in euro con punto decimale
- euristiche per consumi `kWh`, POD, periodo fatturato e potenza impegnata
- pattern mirati per gestire layout reali come Octopus Energy
- estrazione dei dettagli economici dalla sezione `Elementi di dettaglio`
- ricostruzione dei consumi per fascia `F1/F2/F3` a partire dalle letture

## Limiti attuali

- Funziona meglio su PDF testuali; su PDF scannerizzati servira' una fase OCR.
- Alcuni fornitori usano etichette molto diverse: in quei casi il CSV viene comunque prodotto, ma con piu' campi vuoti.
- Questa prima versione e' rule-based, quindi non usa ancora un modello AI per interpretare layout molto anomali.

## Estensione consigliata

Se vuoi, nel passo successivo posso evolverlo in una versione piu' intelligente in uno di questi modi:

1. script Python con fallback LLM per interpretare bollette molto diverse
2. piccola webapp drag-and-drop
3. Google Apps Script collegato a Drive e Sheets

La base attuale e' pensata proprio per essere estesa in quella direzione senza buttare via il lavoro.
