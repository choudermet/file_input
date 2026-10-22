import pandas as pd
from extraction.tables import clean_value
from datetime import datetime


def extract_default_vpg_settings(excel_file: str, print_output: bool = True) -> dict:
    df = pd.read_excel(
        excel_file,
        sheet_name="Default VPG Settings",
        engine="openpyxl",
        header=None,
    )

    data = {}

    # Default Sites
    for i, row in df.iterrows():
        if row[0] == "Protected Site":
            data["protected_site"] = row[1]

        if row[0] == "Recovery Site":
            data["recovery_site"] = row[1]

    # Default VPG Settings block
    for i, row in df.iterrows():
        key = clean_value(row[0])
        value = clean_value(row[1])
        unit = clean_value(row[2]) if len(row) > 2 else None

        if key == "VPG Type":
            data["vpg_type"] = value

        elif key == "Priority":
            data["priority"] = value

        elif key == "Journal History":
            data["journal_history"] = {
                "value": value,
                "unit": unit,
            }

        elif key == "Target RPO Alert":
            data["target_rpo_alert"] = {
                "value": value,
                "unit": unit,
            }

        elif key == "Test Reminder":
            data["test_reminder"] = value

        elif key == "Journal Size Hard Limit Value":
            data["journal_size_hard_limit"] = {
                "value": value,
                "unit": unit,
            }

        elif key == "Journal Size Warning Threshold":
            data["journal_size_warning"] = {
                "value": value,
                "unit": unit,
            }

        elif key == "Scratch Journal Size Hard Limit Value":
            data["scratch_journal_size_hard_limit"] = {
                "value": value,
                "unit": unit,
            }

        elif key == "Scratch Journal Size Warning Threshold":
            data["scratch_journal_size_warning"] = {
                "value": value,
                "unit": unit,
            }

        elif key == "Enable WAN Traffic Compression?":
            data["wan_compression"] = value

        elif key == "Disk Provisioning Override":
            data["disk_provisioning_override"] = value

        elif key == "Recovery Folder Name":
            data["recovery_folder_name"] = value

        elif key == "Volume Sync Type":
            data["volume_sync_type"] = value

        elif key == "Recovery Script Execution Timeout (Seconds)":
            data["pre_recovery_script_execution_timeout_seconds"] = value
            data["post_recovery_script_execution_timeout_seconds"] = unit

        elif key == "Create new MAC address":
            data["failover_live_move_create_new_mac_address"] = value
            data["failover_test_create_new_mac_address"] = unit

        elif key == "Change vNIC IP Config":
            data["failover_live_move_change_vnic_ip_config"] = value
            data["failover_test_change_vnic_ip_config"] = unit

        elif key == "Subnet Mask":
            data["failover_live_move_subnet_mask"] = value
            data["failover_test_subnet_mask"] = unit

        elif key == "Default Gateway":
            data["failover_live_move_default_gateway"] = value
            data["failover_test_default_gateway"] = unit

        elif key == "Preferred DNS Server":
            data["failover_live_move_preferred_dns_server"] = value
            data["failover_test_preferred_dns_server"] = unit

        elif key == "Alternate DNS Server":
            data["failover_live_move_alternate_dns_server"] = value
            data["failover_test_alternate_dns_server"] = unit

        elif key == "DNS Suffix":
            data["failover_live_move_dns_suffix"] = value
            data["failover_test_dns_suffix"] = unit

        elif key == "Run at (HH:MI)":
            if isinstance(row[1], datetime):
                value = row[1].time().isoformat()
            data["extended_journal_run_at"] = value

        elif key == "Number of automatic retry commands":
            data["extended_journal_retry_count"] = value

        elif key == "Wait time between retries (minutes)":
            data["extended_journal_wait_between_retries_minutes"] = value

    if print_output:
        print_default_vpg_settings(data)

    return data


def print_default_vpg_settings(data: dict) -> None:
    print("\nDefault VPG Settings")
    print("--------------------")
    print_key_values({
        "Protected Site": data.get("protected_site"),
        "Recovery Site": data.get("recovery_site"),
        "VPG Type": data.get("vpg_type"),
        "Priority": data.get("priority"),
        "Journal History": format_value_unit(data.get("journal_history")),
        "Target RPO Alert": format_value_unit(data.get("target_rpo_alert")),
        "Test Reminder": data.get("test_reminder"),
        "Journal Size Hard Limit": format_value_unit(
            data.get("journal_size_hard_limit"),
        ),
        "Journal Size Warning": format_value_unit(data.get("journal_size_warning")),
        "Scratch Journal Size Hard Limit": format_value_unit(
            data.get("scratch_journal_size_hard_limit"),
        ),
        "Scratch Journal Size Warning": format_value_unit(
            data.get("scratch_journal_size_warning"),
        ),
        "WAN Compression": data.get("wan_compression"),
    })


def print_key_values(rows: dict) -> None:
    for label, value in rows.items():
        print(f"- {label}: {format_display_value(value)}")


def format_value_unit(value_unit: dict | None) -> str | None:
    if not value_unit:
        return None

    value = value_unit.get("value")
    unit = value_unit.get("unit")

    if value is None and unit is None:
        return None

    if value is None:
        return str(unit)

    if unit is None:
        return f"{value:g}"

    return f"{value:g} {unit}"


def format_display_value(value) -> str:
    if value is None:
        return "Not set"

    return str(value)
