# VCA Check

VCA Check reads a VCA Excel workbook, checks the data, and writes JSON files that can be handed to the next step in the workflow.

The main handoff file for VCA Run is:

```text
outputs/VCA Data_VCA.json
```

VCA Run is expected to take that manifest, resolve workbook names to real platform identifiers, and then prepare the final payload used to create objects in Zerto.

## What It Does

- Opens the workbook from the `files` folder.
- Extracts the workbook sheets into Python data structures.
- Validates the extracted data against the VCA rules.
- Stops at the first failed validation section.
- Writes JSON output only when validation passes.

## Validated Sheets

Validation currently runs in this order:

```text
Zerto Data
Hypervisor Data
Default VPG Settings
Recovery ZVM Sites
VPGs
VM Replication
VM Storage
VM NICs
```

The order matters. Later sheets often depend on reference data from earlier sheets, so the program stops when a section fails instead of continuing with validations that are likely to cascade.

## Project Structure

```text
.
├── config.py
├── extraction/
├── files/
├── ingestion/
├── main.py
├── outputs/
├── payload/
├── requirements.txt
└── validation/
```

The important folders are:

```text
ingestion/    workbook loading and required sheet checks
extraction/   reading workbook data into Python dictionaries/lists
validation/   workbook validation rules
payload/      JSON output builders
outputs/      generated files
```

## Python Version

This project is developed and tested with:

```text
Python 3.14.3
```

## Setup

### Linux

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Windows

Install Python if it is not already installed, then open PowerShell in the project directory.

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

## Run

### Linux

Supply the workbook with the required `--input-file` option:

```bash
python3 main.py --input-file "files/your-workbook.xlsx"
```

You can also supply just a filename or an absolute path:

```bash
python3 main.py --input-file "VCA Data - v0.111.xlsx"
python3 main.py --input-file "/path/to/VCA Data.xlsx"
```

### Windows

Supply the workbook with the required `--input-file` option:

```powershell
py main.py --input-file "files\your-workbook.xlsx"
```

You can also supply just a filename or an absolute path:

```powershell
py main.py --input-file "VCA Data - v0.111.xlsx"
py main.py --input-file "C:\path\to\VCA Data.xlsx"
```

The `--input-file` option is required. Use `python3 main.py --help` on Linux or
`py main.py --help` on Windows to show the command-line usage. If the selected
workbook does not exist, the program reports the resolved path and exits before
validation starts.

If validation passes, the program writes:

```text
outputs/<input-name>_vca_check_dump.json
outputs/<input-name>_VCA.json
outputs/<input-name>_site_settings.json
```

`<input-name>` is the workbook filename without `.xlsx`. The generated JSON files
for that workbook are removed at the beginning of every run. If validation fails,
the program prints the failed section, writes the same error details to
`outputs/<input-name>_validation_errors.json`, and stops without leaving successful
output from a previous run.

## Log File

Every run writes a timestamped log file in the dedicated `files/logs` folder,
which is created automatically. For example:

```text
files/logs/VCA Data_2026-09-21-14-55-57.log
```

Logging is fully enabled by default. The file records `TRACE`, `DEBUG`, `INFO`,
`WARNING`, and `ERROR` messages when those events occur. It includes the workbook-reading, data-extraction, inheritance,
validation, and output-generation steps, along with validation failures.

## Workbook File

VCA Check takes its workbook only from the required `--input-file` option. Supply
either a filename in the `files` folder or a relative or absolute path; no
source-code change is required.

## Output Files

### `outputs/<input-name>_validation_errors.json`

This file is written when worksheet or manifest validation fails. It records the
failed section and the same error messages displayed in the terminal.

### `outputs/<input-name>_vca_check_dump.json`

This is the diagnostic dump. It is useful when you need to understand what the program extracted and how defaults were applied.

It includes:

- source workbook name
- validation status
- validation details
- reference data
- raw candidate payload data
- resolved candidate payload data

The resolved data is important because some workbook fields can be blank and still have an effective value inherited from another sheet.

### `outputs/<input-name>_VCA.json`

This is the VCA Run manifest. It uses PascalCase section names and is written as a list of VPG definitions.

Example section names:

```text
Basic
Labels
BootGroup
Scripting
Recovery
Journal
Scratch
Networks
VMs
```

This is the file VCA Run should consume. It contains the validated VPG definitions from the workbook. VCA Run should resolve names such as sites, VMs, hosts, datastores, networks, folders, volumes, and NICs into real identifiers before making the POST/PUT API calls to Zerto.

### `outputs/<input-name>_site_settings_<timestamp>.json`

This file contains the data extracted from the workbook's Site Settings sheet.
It is written when validation succeeds, alongside the diagnostic dump and VCA Run
manifest. `<timestamp>` uses the computer's local time in `YYYY-MM-DD HH-MM-SS`
format.

It includes:

- `SiteInformation`: site location and contact details
- `Throttling`: replication bandwidth limits and time windows
- `Policies`: commit policies, timeouts, and replication options
- `AdvancedResilience`: offline recovery mode settings
- `EncryptionDetection`: encryption analyzer settings

## Defaults and Effective Values

Some workbook values can be inherited.

For example, a VPG may inherit values from:

```text
Recovery ZVM Sites
Default VPG Settings
```

VM-level rows may also inherit values from the VPG they belong to.

VCA Check validates the workbook in inheritance order, starting with the source
and default values before validating the sheets that use them. Therefore, any
invalid inherited value will already have been reported against the sheet where
it was originally defined.

After validation succeeds, the resolved candidate payload in:

```text
outputs/<input-name>_vca_check_dump.json
```

can be used to see the effective values produced after defaults and inherited
values have been applied.

## Notes

- `main.py` is the normal entry point.
- Validation is the gate before JSON generation.
- `payload/manifest_output.py` builds the VCA Run manifest.
- `payload/json_output.py` builds the diagnostic dump.
- `payload/site_settings.py` writes the Site Settings JSON.
- `payload/validation_errors.py` writes the error report when validation fails.
- The project currently checks workbook readiness and prepares handoff JSON. Creating objects in Zerto belongs to the VCA Run side.