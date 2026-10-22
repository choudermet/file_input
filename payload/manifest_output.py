import json
from pathlib import Path
from datetime import datetime

RUN_TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

from extraction.tables import clean_value
from payload.json_output import (
    duration_to_hours,
    duration_to_seconds,
    effective_disk_provisioning_to_is_thin,
    first_value,
    is_dhcp,
    make_json_safe,
    rows_for_vm,
    rows_for_vpg,
    should_replace_ip_configuration,
    test_reminder_to_minutes,
    yes_no_to_bool,
)


def build_manifest_output_file(excel_file: str | Path) -> Path:
    return Path("outputs") / (
        f"{Path(excel_file).stem}_VCA_{RUN_TIMESTAMP}.json"
    )


class ManifestValidationError(ValueError):
    def __init__(self, messages: list[str]):
        self.messages = messages
        super().__init__("\n".join(messages))


def write_vca_run_manifest(
    excel_file: str | Path,
    resolved_api_candidate_payloads: dict,
    boot_order_groups: list[dict],
    output_file: str | Path | None = None,
) -> Path:
    manifest = build_vca_run_manifest(
        resolved_api_candidate_payloads,
        boot_order_groups,
    )
    validate_manifest_required_values(manifest)
    output_manifest = pascalize_manifest_keys(manifest)

    output_path = (
        Path(output_file)
        if output_file
        else build_manifest_output_file(excel_file)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            make_json_safe(output_manifest),
            indent=2,
        ),
        encoding="utf-8",
    )

    return output_path


def pascalize_manifest_keys(value):
    if isinstance(value, list):
        return [
            pascalize_manifest_keys(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            pascalize_manifest_key(key): pascalize_manifest_keys(item)
            for key, item in value.items()
        }

    return value


def pascalize_manifest_key(key) -> str:
    key = str(key)
    special_cases = {
        "BootGroup": "BootGroups",
        "VMs": "Vms",
        "nics": "Nics",
        "vcd": "VCD",
        "rdm": "RDM",
        "ipConfig": "IpConfig",
        "isDhcp": "IsDhcp",
    }

    if key in special_cases:
        return special_cases[key]

    return key[:1].upper() + key[1:]


def build_vca_run_manifest(
    resolved_api_candidate_payloads: dict,
    boot_order_groups: list[dict],
) -> list[dict]:
    vpgs = resolved_api_candidate_payloads["vpgs"]
    vm_replication = resolved_api_candidate_payloads["vm_replication"]
    vm_storage = resolved_api_candidate_payloads["vm_storage"]
    vm_nics = resolved_api_candidate_payloads["vm_nics"]

    return [
        build_manifest_vpg(
            row,
            rows_for_vpg(vm_replication, row.get("VPG Name")),
            rows_for_vpg(vm_storage, row.get("VPG Name")),
            rows_for_vpg(vm_nics, row.get("VPG Name")),
            boot_order_groups,
        )
        for row in vpgs
    ]


def validate_manifest_required_values(manifest: list[dict]) -> None:
    errors = []

    for vpg in manifest:
        vpg_name = value_at(vpg, "Basic", "name") or "<unknown VPG>"

        validate_manifest_journal_datastores(
            errors,
            vpg_name,
            vpg,
            "Journal",
        )
        validate_manifest_journal_datastores(
            errors,
            vpg_name,
            vpg,
            "Scratch",
        )
        validate_manifest_nic_networks(errors, vpg_name, vpg)

    if errors:
        raise ManifestValidationError(errors)


def validate_manifest_journal_datastores(
    errors: list[str],
    vpg_name: str,
    vpg: dict,
    section_name: str,
) -> None:
    has_vpg_datastore = has_datastore_identifier(vpg.get(section_name, {}))

    for vm in vpg.get("VMs", []):
        vm_name = vm.get("vmIdentifier") or "<unknown VM>"
        if has_datastore_identifier(vm.get(section_name, {})) or has_vpg_datastore:
            continue

        errors.append(
            f"{section_name} datastore is missing for VPG '{vpg_name}', "
            f"VM '{vm_name}'. Provide either {section_name} datastoreIdentifier "
            f"or datastoreClusterIdentifier at VM level or VPG level."
        )


def validate_manifest_nic_networks(
    errors: list[str],
    vpg_name: str,
    vpg: dict,
) -> None:
    if value_at(vpg, "Basic", "vpgType") in ("Local Continuous Backup", "Local"):
        return

    network_checks = (
        ("failover", "Failover Live / Move"),
        ("failoverTest", "Failover Test"),
    )

    for network_key, label in network_checks:
        vpg_network = value_at(
            vpg,
            "Networks",
            network_key,
            "hypervisor",
            "defaultNetworkIdentifier",
        )

        for vm in vpg.get("VMs", []):
            vm_name = vm.get("vmIdentifier") or "<unknown VM>"
            for nic in vm.get("nics", []):
                nic_name = nic.get("nicIdentifier") or "<unknown NIC>"
                nic_network = value_at(
                    nic,
                    network_key,
                    "hypervisor",
                    "networkIdentifier",
                )
                if clean_value(nic_network) is not None or clean_value(vpg_network) is not None:
                    continue

                errors.append(
                    f"{label} network is missing for VPG '{vpg_name}', "
                    f"VM '{vm_name}', NIC '{nic_name}'. Provide either NIC "
                    f"networkIdentifier or VPG defaultNetworkIdentifier."
                )


def has_datastore_identifier(section: dict) -> bool:
    return (
        clean_value(section.get("datastoreIdentifier")) is not None
        or clean_value(section.get("datastoreClusterIdentifier")) is not None
    )


def value_at(data: dict, *keys):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)

    return current


def build_manifest_vpg(
    row: dict,
    vm_replication: list[dict],
    vm_storage: list[dict],
    vm_nics: list[dict],
    boot_order_groups: list[dict],
) -> dict:
    return {
        "Basic": build_manifest_basic(row),
        "Labels": build_manifest_labels(row),
        "LongTermRetention": None, 
        "BootGroup": build_manifest_boot_group(
            boot_order_groups,
            row.get("Boot Order Meta Group Name"),
        ),
        "Scripting": build_manifest_scripting(row),
        "Recovery": build_manifest_recovery(row),
        "Journal": build_manifest_journal(row),
        "Scratch": build_manifest_scratch(row),
        "Networks": build_manifest_networks(row),
        "VMs": build_manifest_vms(vm_replication, vm_storage, vm_nics),
        "Protected": build_manifest_protected(),
        "Generation": 0,
    }


def build_manifest_protected() -> dict:
    return {
        "vcd": None,
    }


def build_manifest_labels(row: dict) -> dict:
    return {
        "Label1": row.get("Label 1"),
        "Label2": row.get("Label 2"),
        "Label3": row.get("Label 3"),
        "Label4": row.get("Label 4"),
        "Label5": row.get("Label 5"),
    }


def build_manifest_basic(row: dict) -> dict:
    return {
        "name": row.get("VPG Name"),
        "vpgType": normalize_vpg_type(row.get("VPG Type")),
        "rpoInSeconds": duration_to_seconds(
            row.get("Target RPO Alert Value"),
            row.get("Target RPO Alert Unit"),
        ),
        "testIntervalInMinutes": test_reminder_to_minutes(row.get("Test Reminder")),
        "journalHistoryInHours": duration_to_hours(
            row.get("Journal History Value"),
            row.get("Journal History Unit"),
        ),
        "priority": row.get("Priority"),
        "useWanCompression": yes_no_to_bool(row.get("Enable WAN Traffic Compression")),
        "serviceProfileIdentifier": None,
        "zorgIdentifier": None,
        "protectedSiteIdentifier": row.get("Effective Protected ZVM Site Name"),
        "recoverySiteIdentifier": row.get("Effective Recovery ZVM Site Name"),
    }


def normalize_vpg_type(value):
    vpg_types = {
        "Remote DR and Continuous Backup": "Remote",
        "Cyber Recovery": "Cyber",
        "Local Continuous Backup": "Local",
        "Data Mobility and Migration": "Migrate",
    }

    cleaned_value = clean_value(value)
    return vpg_types.get(cleaned_value, cleaned_value)


def build_manifest_boot_group(
    boot_order_groups: list[dict],
    meta_group_name,
) -> dict:
    return {
        "bootGroups": [
            {
                "bootGroupIdentifier": None,
                "name": group.get("group_name"),
                "bootDelayInSeconds": to_int_or_none(group.get("boot_delay_secs")),
            }
            for group in boot_order_groups
            if clean_value(group.get("meta_group_name")) == clean_value(meta_group_name)
        ],
    }


def to_int_or_none(value) -> int | None:
    cleaned_value = clean_value(value)
    if cleaned_value is None:
        return None

    return int(float(cleaned_value))


def build_manifest_scripting(row: dict) -> dict:
    return {
        "preRecovery": build_manifest_script(row, "Pre-Recovery"),
        "postRecovery": build_manifest_script(row, "Post-Recovery"),
        "postBackup": {
            "command": None,
            "parameters": None,
            "timeoutInSeconds": 0,
        },
    }


def build_manifest_script(row: dict, prefix: str) -> dict:
    return {
        "command": row.get(f"{prefix} Script Name"),
        "parameters": row.get(f"{prefix} Script Parameters"),
        "timeoutInSeconds": row.get(f"{prefix} Script Execution Timeout (Seconds)"),
    }


def build_manifest_recovery(row: dict) -> dict:
    return {
        "defaultHostIdentifier": row.get("Recovery Host Name"),
        "defaultHostClusterIdentifier": row.get("Recovery Host Name"),
        "defaultDatastoreIdentifier": row.get("Recovery Datastore Name"),
        "defaultDatastoreClusterIdentifier": row.get("Recovery Datastore Name"),
        "defaultFolderIdentifier": row.get("Recovery Folder Name"),
        "resourcePoolIdentifier": None,
        "vcd": {
            "orgVdcIdentifier": None,
        },
        "publicCloud": None,
    }


def build_manifest_journal(row: dict) -> dict:
    return {
        "limitation": build_manifest_limitation(
            row.get("Journal Size Hard Limit Value"),
            row.get("Journal Size Hard Limit Unit"),
            row.get("Journal Size Warning Threshold Value"),
            row.get("Journal Size Warning Threshold Unit"),
        ),
        "datastoreIdentifier": row.get("Journal Datastore Name"),
        "datastoreClusterIdentifier": row.get("Journal Datastore Name"),
    }


def build_manifest_scratch(row: dict) -> dict:
    return {
        "limitation": build_manifest_limitation(
            row.get("Scratch Journal Size Hard Limit Value"),
            row.get("Scratch Journal Size Hard Limit Unit"),
            row.get("Scratch Journal Size Warning Threshold Value"),
            row.get("Scratch Journal Size Warning Threshold Unit"),
        ),
        "datastoreIdentifier": row.get("Scratch Journal Datastore Name"),
        "datastoreClusterIdentifier": row.get("Scratch Journal Datastore Name"),
    }


def build_manifest_limitation(
    hard_limit_value,
    hard_limit_unit,
    warning_value,
    warning_unit,
) -> dict:
    hard_limit_in_mb, hard_limit_in_percent = limit_value_pair(
        hard_limit_value,
        hard_limit_unit,
    )
    warning_threshold_in_mb, warning_threshold_in_percent = limit_value_pair(
        warning_value,
        warning_unit,
    )

    return {
        "hardLimitInMB": hard_limit_in_mb,
        "hardLimitInPercent": hard_limit_in_percent,
        "warningThresholdInMB": warning_threshold_in_mb,
        "warningThresholdInPercent": warning_threshold_in_percent,
    }


def limit_value_pair(value, unit) -> tuple[int | float | None, int | float | None]:
    cleaned_value = clean_value(value)
    cleaned_unit = clean_value(unit)

    if cleaned_unit == "Unlimited":
        return 0, 0

    if cleaned_value is None or cleaned_unit is None:
        return 0, 0

    if cleaned_unit == "%":
        return 0, cleaned_value

    if cleaned_unit == "GiB":
        return int(float(cleaned_value) * 1024), 0

    if cleaned_unit == "TiB":
        return int(float(cleaned_value) * 1024 * 1024), 0

    return 0, 0


def build_manifest_networks(row: dict) -> dict:
    return {
        "failover": build_manifest_default_network(
            row.get("Failover Live / Move - Network Name"),
        ),
        "failoverTest": build_manifest_default_network(
            first_value(
                row.get("Failover Test - Network Name"),
                row.get("Failover Test Network Name"),
            ),
        ),
    }


def build_manifest_default_network(network_name) -> dict:
    return {
        "vcd": None,
        "hypervisor": {
            "defaultNetworkIdentifier": network_name,
        },
        "publicCloud": None,
    }


def build_manifest_vms(
    vm_replication: list[dict],
    vm_storage: list[dict],
    vm_nics: list[dict],
) -> list[dict]:
    vm_names = []
    for row in vm_replication + vm_storage + vm_nics:
        vm_name = clean_value(row.get("VM Name"))
        if vm_name and vm_name not in vm_names:
            vm_names.append(vm_name)

    return [
        {
            "vmIdentifier": vm_name,
            "Recovery": build_manifest_vm_recovery(first_row_for_vm(vm_replication, vm_name)),
            "bootGroupIdentifier": build_manifest_vm_boot_group_identifier(
                first_row_for_vm(vm_replication, vm_name),
            ),
            "Journal": build_manifest_journal(first_row_for_vm(vm_replication, vm_name) or {}),
            "Scratch": build_manifest_scratch(first_row_for_vm(vm_replication, vm_name) or {}),
            "Volumes": [
                build_manifest_volume(row)
                for row in rows_for_vm(vm_storage, vm_name)
            ],
            "nics": [
                build_manifest_nic(row)
                for row in rows_for_vm(vm_nics, vm_name)
            ],
        }
        for vm_name in vm_names
    ]


def first_row_for_vm(rows: list[dict], vm_name) -> dict | None:
    matching_rows = rows_for_vm(rows, vm_name)
    if not matching_rows:
        return None

    return matching_rows[0]


def build_manifest_vm_recovery(row: dict | None) -> dict:
    row = row or {}
    return {
        "hostIdentifier": row.get("Recovery Host Name"),
        "hostClusterIdentifier": row.get("Recovery Host Name"),
        "datastoreIdentifier": row.get("Recovery Datastore Name"),
        "datastoreClusterIdentifier": row.get("Recovery Datastore Name"),
        "folderIdentifier": row.get("Recovery Folder Name"),
        "resourcePoolIdentifier": None,
        "vcd": {
            "storagePolicyIdentifier": None,
        },
        "publicCloud": None,
        "useVmEncryption": False,
    }


def build_manifest_vm_boot_group_identifier(row: dict | None):
    if row is None:
        return None

    return row.get("Boot Order Group Name")


def build_manifest_volume(row: dict) -> dict:
    return {
        "volumeIdentifier": first_value(
            row.get("SCSI ID"),
            row.get("Protected Volume Location"),
        ),
        "vcd": None,
        "preseed": None,
        "rdm": None,
        "datastore": {
            "datastoreClusterIdentifier": row.get("Recovery Datastore Name"),
            "datastoreIdentifier": row.get("Recovery Datastore Name"),
            "isThin": effective_disk_provisioning_to_is_thin(
                row.get("Disk Provisioning Override"),
                row.get("Provisioning"),
            ),
        },
        "volumeSyncSettings": normalize_volume_sync_settings(
            row.get("Volume Sync Type"),
        ),
    }


def normalize_volume_sync_settings(value):
    sync_settings = {
        "Continuous Sync": "ContinuousSync",
    }

    cleaned_value = clean_value(value)
    return sync_settings.get(cleaned_value, cleaned_value)


def build_manifest_nic(row: dict) -> dict:
    return {
        "nicIdentifier": row.get("NIC Name"),
        "failoverTest": build_manifest_nic_network(row, "Failover Test"),
        "failover": build_manifest_nic_network(row, "Failover Live / Move"),
    }


def build_manifest_nic_network(row: dict, prefix: str) -> dict:
    return {
        "hypervisor": {
            "networkIdentifier": row.get(f"{prefix} - Network Name"),
            "shouldReplaceMacAddress": yes_no_to_bool(
                row.get(f"{prefix} - Create new MAC address"),
            ),
            "dnsSuffix": row.get(f"{prefix} - DNS Suffix"),
            "ipConfig": build_manifest_ip_config(row, prefix),
            "isDhcp": is_dhcp(row.get(f"{prefix} - Change vNIC IP Config")),
            "shouldReplaceIpConfiguration": should_replace_ip_configuration(
                row.get(f"{prefix} - Change vNIC IP Config"),
            ),
        },
        "vcd": None,
        "publicCloud": None,
    }


def build_manifest_ip_config(row: dict, prefix: str) -> dict | None:
    if row.get(f"{prefix} - Change vNIC IP Config") != "Yes, Static":
        return None

    return {
        "staticIp": row.get(f"{prefix} - IP Address"),
        "subnetMask": row.get(f"{prefix} - Subnet Mask"),
        "gateway": row.get(f"{prefix} - Default Gateway"),
        "primaryDns": row.get(f"{prefix} - Preferred DNS Server"),
        "secondaryDns": row.get(f"{prefix} - Alternate DNS Server"),
    }
