import pandas as pd
import config
from extraction.tables import clean_records


def extract_zerto_data(excel_file: str) -> dict:
    raw_df = pd.read_excel(
        excel_file,
        sheet_name="Zerto Data",
        engine="openpyxl",
        header=None,
    )

    header_row_index = None

    for index, row in raw_df.iterrows():
        row_values = [
            str(value).strip()
            for value in row.tolist()
            if pd.notna(value)
        ]

        if "ZVM Site Name" in row_values:
            header_row_index = index
            break

    if header_row_index is None:
        raise ValueError("Could not find header row containing 'ZVM Site Name'")

    df = pd.read_excel(
        excel_file,
        sheet_name="Zerto Data",
        engine="openpyxl",
        header=header_row_index,
    )

    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")
    df = df.where(pd.notnull(df), None)

    records = []
    metadata = []

    for index, row in df.iterrows():
        records.append(row.to_dict())
        metadata.append({
            "__sheet_name": "Zerto Data",
            "__excel_row": header_row_index + index + 2,
        })

    records = clean_records(records, metadata)
    summary = build_zerto_summary(records)

    load_zerto_summary_into_config(summary)

    return {
        "dataframe": df,
        "records": records,
        "columns": list(df.columns),
        "summary": summary,
    }


def build_zerto_summary(records: list[dict]) -> dict:
    summary = {
        "zvm_sites": [],
        "labels": {
            "scopes": [],
            "waves": [],
            "application_names": [],
            "application_environments": [],
            "data_types": [],
        },
        "recovery_scripts": [],
        "boot_order_groups": [],
    }

    for row in records:
        if row.get("ZVM Site Name"):
            summary["zvm_sites"].append({
                "site_name": row.get("ZVM Site Name"),
                "zerto_version": row.get("Zerto Version"),
                "protected": row.get("Protected?"),
                "recovery": row.get("Recovery?"),
            })

        if row.get("Label 1"):
            summary["labels"]["scopes"].append(row.get("Label 1"))

        if row.get("Label 2"):
            summary["labels"]["waves"].append(row.get("Label 2"))

        if row.get("Label 3"):
            summary["labels"]["application_names"].append(row.get("Label 3"))

        if row.get("Label 4"):
            summary["labels"]["application_environments"].append(row.get("Label 4"))

        if row.get("Label 5"):
            summary["labels"]["data_types"].append(row.get("Label 5"))

        if row.get("Recovery Script Name"):
            summary["recovery_scripts"].append(row.get("Recovery Script Name"))

        if row.get("Group Name"):
            summary["boot_order_groups"].append({
                "group_id": row.get("Group ID"),
                "meta_group_name": row.get("Meta Group Name"),
                "group_name": row.get("Group Name"),
                "boot_delay_secs": row.get("Boot Delay (Secs)"),
            })

    return summary


def load_zerto_summary_into_config(summary: dict) -> None:
    config.zvm_site_names = [
        site["site_name"]
        for site in summary["zvm_sites"]
    ]

    config.protected_site_names = [
        site["site_name"]
        for site in summary["zvm_sites"]
        if site["protected"] == "Yes"
    ]

    config.recovery_site_names = [
        site["site_name"]
        for site in summary["zvm_sites"]
        if site["recovery"] == "Yes"
    ]

    config.scopes = summary["labels"]["scopes"]
    config.waves = summary["labels"]["waves"]
    config.application_names = summary["labels"]["application_names"]
    config.application_environments = summary["labels"]["application_environments"]
    config.data_types = summary["labels"]["data_types"]

    config.recovery_scripts = summary["recovery_scripts"]

    config.boot_order_groups = [
        group["group_name"]
        for group in summary["boot_order_groups"]
    ]
    config.boot_order_groups_by_meta_group = {}
    for group in summary["boot_order_groups"]:
        meta_group_name = group.get("meta_group_name")
        group_name = group.get("group_name")

        if meta_group_name and group_name:
            config.boot_order_groups_by_meta_group.setdefault(
                meta_group_name,
                [],
            ).append(group_name)

    config.boot_order_meta_groups = [
        group["meta_group_name"]
        for group in summary["boot_order_groups"]
    ]
