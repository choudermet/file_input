from datetime import date, datetime, time
import ipaddress
from typing import Any

import pandas as pd


VALID_SUBNET_MASKS_BY_DIGITS = {}

for prefix_length in range(33):
    network = ipaddress.IPv4Network(f"0.0.0.0/{prefix_length}")
    subnet_mask = str(network.netmask)
    digits = subnet_mask.replace(".", "")

    VALID_SUBNET_MASKS_BY_DIGITS[digits] = subnet_mask
    VALID_SUBNET_MASKS_BY_DIGITS[str(int(digits))] = subnet_mask


def extract_sheet_table(
    excel_file: str,
    sheet_name: str,
    required_header: str,
    table_name: str | None = None,
) -> list[dict]:
    raw_df = pd.read_excel(
        excel_file,
        sheet_name=sheet_name,
        engine="openpyxl",
        header=None,
    )

    header_row_index = find_header_row(raw_df, required_header)

    df = pd.read_excel(
        excel_file,
        sheet_name=sheet_name,
        engine="openpyxl",
        header=header_row_index,
    )

    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")

    records = []
    metadata = []
    resolved_table_name = table_name or sheet_name

    for index, row in df.iterrows():
        records.append(row.to_dict())
        metadata.append({
            "__sheet_name": sheet_name,
            "__table_name": resolved_table_name,
            "__excel_row": header_row_index + index + 2,
        })

    return clean_records(records, metadata)


def find_header_row(df: pd.DataFrame, required_text: str) -> int:
    for index, row in df.iterrows():
        values = [
            str(value).strip()
            for value in row.tolist()
            if pd.notna(value)
        ]

        if required_text in values:
            return index

    raise ValueError(f"Could not find header row containing '{required_text}'")


def clean_records(
    records: list[dict],
    metadata: list[dict] | None = None,
) -> list[dict]:
    cleaned_records = []

    for index, record in enumerate(records):
        cleaned_record = {}

        for key, value in record.items():
            if key is None or str(key).strip() == "nan":
                continue

            cleaned_key = str(key).strip()
            cleaned_value = clean_value(value)

            if cleaned_key.endswith("Subnet Mask"):
                cleaned_value = normalize_subnet_mask(cleaned_value)

            cleaned_record[cleaned_key] = cleaned_value

        if any(value is not None for value in cleaned_record.values()):
            if metadata:
                cleaned_record.update(metadata[index])

            if "__table_row_id" not in cleaned_record:
                if "ID" in cleaned_record:
                    cleaned_record["__table_row_id"] = cleaned_record.get("ID")
                else:
                    cleaned_record["__table_row_id"] = len(cleaned_records) + 1

            cleaned_records.append(cleaned_record)

    return cleaned_records


def clean_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, float) and pd.isna(value):
        return None

    if pd.isna(value) if not isinstance(value, (list, dict)) else False:
        return None

    if isinstance(value, str):
        value = value.strip()
        return value or None

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    return value


def normalize_subnet_mask(value):
    cleaned_value = clean_value(value)

    if cleaned_value is None:
        return None

    if isinstance(cleaned_value, float) and cleaned_value.is_integer():
        text = str(int(cleaned_value))
    else:
        text = str(cleaned_value).strip()

    if "." in text:
        return text

    return VALID_SUBNET_MASKS_BY_DIGITS.get(text, text)
