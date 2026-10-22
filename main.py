import argparse
import logging
import traceback
from pathlib import Path

from pydantic import ValidationError

from logging_config import setup_logging, trace
from ingestion.reader import load_excel_workbook, validate_required_sheets
from extraction.zerto_data import extract_zerto_data
from extraction.hypervisor import extract_hypervisor_data
from extraction.vpg_settings import extract_default_vpg_settings
from extraction.recovery_zvm_sites import extract_recovery_zvm_sites
from extraction.site_settings import extract_site_settings
from extraction.tables import extract_sheet_table
from extraction.vpgs import extract_vpgs
from validation.default_vpg_settings import validate_default_vpg_settings
from validation.zerto_data import validate_zerto_data
from validation.hypervisor import validate_hypervisor_data
from validation.recovery_zvm_sites import validate_recovery_zvm_sites
from validation.vpgs import validate_vpgs
from validation.vm_replication import validate_vm_replication
from validation.vm_storage import validate_vm_storage
from validation.vm_nics import validate_vm_nics
from validation.error_formatting import WorkbookValidationError, format_validation_errors
from payload.json_output import (
    build_output_file,
    make_json_safe,
    write_zerto_json_dump,
)
from payload.manifest_output import (
    ManifestValidationError,
    build_manifest_output_file,
)
from payload.site_settings import (
    build_site_settings_file,
    write_site_settings_json,
)
from payload.validation_errors import (
    build_validation_errors_file,
    write_validation_errors,
)


def raw_log(label: str, value=None) -> None:
    if value is None:
        trace("%s", label)
        return

    trace("%s: %r", label, value)


def resolve_workbook_path(value: str) -> Path:
    workbook_path = Path(value).expanduser()
    if workbook_path.parent == Path("."):
        workbook_path = Path("files") / workbook_path

    return workbook_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a VCA Excel workbook and generate JSON output.",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        metavar="WORKBOOK",
        help="workbook path, or a filename in the files folder",
    )
    args = parser.parse_args()
    args.input_file = resolve_workbook_path(args.input_file)
    if not args.input_file.is_file():
        parser.error(f"workbook not found: {args.input_file}")

    return args


def clear_generated_output_files(output_files: tuple[str | Path, ...]) -> None:
    for output_file in output_files:
        output_path = Path(output_file)
        try:
            output_path.unlink()
        except FileNotFoundError:
            continue

        logging.info("Removed output from previous run: %s", output_path)


def main(excel_file: str | Path):
    log_path = setup_logging(excel_file)
    print(f"Log file: {log_path}")

    output_path = build_output_file(excel_file)
    manifest_output_path = build_manifest_output_file(excel_file)
    site_settings_output_path = build_site_settings_file(excel_file)
    validation_errors_path = build_validation_errors_file(excel_file)

    clear_generated_output_files(
        (
            output_path,
            manifest_output_path,
            site_settings_output_path,
            validation_errors_path,
        ),
    )

    excel_file = str(excel_file)
    raw_log("run_started", {"source_file": excel_file})
    logging.info("Starting VCA workbook validation run")
    logging.info("Source workbook: %s", excel_file)
    logging.info("Log file: %s", log_path)

    logging.info("Loading workbook")
    workbook = load_excel_workbook(excel_file)
    validate_required_sheets(workbook)
    raw_log("workbook", {"sheets": workbook.sheetnames})

    print("\nWorkbook loaded successfully")
    logging.info("Workbook loaded successfully")

    logging.info("Extracting workbook data")
    logging.info("Extracting Site Settings")
    site_settings = extract_site_settings(workbook)
    raw_log("extracted.site_settings", site_settings)
    logging.info("Extracting Zerto Data")
    zerto_data = extract_zerto_data(excel_file)
    raw_log("extracted.zerto_data", {
        "columns": zerto_data.get("columns"),
        "summary": zerto_data.get("summary"),
        "records": zerto_data.get("records"),
    })
    logging.info("Extracting Hypervisor Data")
    hypervisor_data = extract_hypervisor_data(excel_file)
    raw_log("extracted.hypervisor_data", hypervisor_data)
    logging.info("Extracting Default VPG Settings")
    vpg_settings = extract_default_vpg_settings(excel_file, print_output=False)
    raw_log("extracted.default_vpg_settings", vpg_settings)
    logging.info("Extracting Recovery ZVM Sites")
    recovery_zvm_sites = extract_recovery_zvm_sites(excel_file)
    raw_log("extracted.recovery_zvm_sites", recovery_zvm_sites)
    logging.info("Extracting VPGs")
    vpgs = extract_vpgs(excel_file)
    raw_log("extracted.vpgs", vpgs)
    logging.info("Extracting VM Replication")
    vm_replication = extract_sheet_table(
        excel_file,
        "VM Replication",
        "VPG Name",
        table_name="VM_Replication",
    )
    raw_log("extracted.vm_replication", vm_replication)
    logging.info("Extracting VM Storage")
    vm_storage = extract_sheet_table(
        excel_file,
        "VM Storage", "VPG Name", table_name="VM_Storage",
    )
    raw_log("extracted.vm_storage", vm_storage)
    logging.info("Extracting VM NICs")
    vm_nics = extract_sheet_table(
        excel_file,
        "VM NICs",
        "VPG Name",
        table_name="VM_NICs",
    )
    raw_log("extracted.vm_nics", vm_nics)
    logging.info("Extracting Extended Journal")
    extended_journal = extract_sheet_table(
        excel_file,
        "Extended Journal",
        "VPG Name",
        table_name="Extended_Journal_Copies",
    )
    raw_log("extracted.extended_journal", extended_journal)
    log_extraction_summary(
        zerto_data,
        hypervisor_data,
        recovery_zvm_sites,
        vpgs,
        vm_replication,
        vm_storage,
        vm_nics,
    )
    validations = {}

    log_validation_started("Zerto Data")
    try:
        result = validate_zerto_data(zerto_data)
        validations["zerto_data"] = validation_passed(result)
        raw_log("validation.zerto_data", validations["zerto_data"])
        print("\nZerto Data validation passed")
        print("----------------------------")
        log_validation_passed("Zerto Data")

    except WorkbookValidationError as error:
        print("\nZerto Data validation failed")
        print("----------------------------")
        print_validation_messages(error.messages)
        log_validation_failed("Zerto Data", error.messages, excel_file)
        validations["zerto_data"] = validation_failed(error.messages)
        raw_log("validation.zerto_data", validations["zerto_data"])
        stop_after_validation_failure("Zerto Data")
        return

    log_validation_started("Hypervisor Data")
    try:
        result = validate_hypervisor_data(hypervisor_data)
        validations["hypervisor_data"] = validation_passed(result)
        raw_log("validation.hypervisor_data", validations["hypervisor_data"])
        print("\nHypervisor Data validation passed")
        print("---------------------------------")
        log_validation_passed("Hypervisor Data")

    except WorkbookValidationError as error:
        print("\nHypervisor Data validation failed")
        print("---------------------------------")
        print_validation_messages(error.messages)
        log_validation_failed("Hypervisor Data", error.messages, excel_file)
        validations["hypervisor_data"] = validation_failed(error.messages)
        raw_log("validation.hypervisor_data", validations["hypervisor_data"])
        stop_after_validation_failure("Hypervisor Data")
        return

    except ValidationError as error:
        messages = format_validation_errors(error)
        print("\nHypervisor Data validation failed")
        print("---------------------------------")
        print_validation_messages(messages)
        log_validation_failed("Hypervisor Data", messages, excel_file)
        validations["hypervisor_data"] = validation_failed(
            messages,
            error.errors(include_url=False),
        )
        raw_log("validation.hypervisor_data", validations["hypervisor_data"])
        stop_after_validation_failure("Hypervisor Data")
        return

    except ValueError as error:
        print("\nHypervisor Data validation failed")
        print("---------------------------------")
        print(f"- {error}")
        log_validation_failed("Hypervisor Data", [str(error)], excel_file)
        validations["hypervisor_data"] = validation_failed([str(error)])
        raw_log("validation.hypervisor_data", validations["hypervisor_data"])
        stop_after_validation_failure("Hypervisor Data")
        return

    log_validation_started("Default VPG Settings")
    try:
        result = validate_default_vpg_settings(vpg_settings)
        validations["default_vpg_settings"] = validation_passed(result)
        raw_log(
            "validation.default_vpg_settings",
            validations["default_vpg_settings"],
        )
        print("\nDefault VPG Settings validation passed")
        print("--------------------------------------")
        log_validation_passed("Default VPG Settings")

    except ValidationError as error:
        messages = format_validation_errors(error)
        print("\nDefault VPG Settings validation failed")
        print("--------------------------------------")
        print_validation_messages(messages)
        log_validation_failed("Default VPG Settings", messages, excel_file)
        validations["default_vpg_settings"] = validation_failed(
            messages,
            error.errors(include_url=False),
        )
        raw_log(
            "validation.default_vpg_settings",
            validations["default_vpg_settings"],
        )
        stop_after_validation_failure("Default VPG Settings")
        return

    log_validation_started("Recovery ZVM Sites")
    try:
        result = validate_recovery_zvm_sites(recovery_zvm_sites, vpg_settings)
        validations["recovery_zvm_sites"] = validation_passed(result)
        raw_log(
            "validation.recovery_zvm_sites",
            validations["recovery_zvm_sites"],
        )
        print("\nRecovery ZVM Sites validation passed")
        print("------------------------------------")
        log_validation_passed("Recovery ZVM Sites")

    except WorkbookValidationError as error:
        print("\nRecovery ZVM Sites validation failed")
        print("------------------------------------")
        print_validation_messages(error.messages)
        log_validation_failed("Recovery ZVM Sites", error.messages, excel_file)
        validations["recovery_zvm_sites"] = validation_failed(error.messages)
        raw_log(
            "validation.recovery_zvm_sites",
            validations["recovery_zvm_sites"],
        )
        stop_after_validation_failure("Recovery ZVM Sites")
        return

    except ValidationError as error:
        messages = format_validation_errors(error)
        print("\nRecovery ZVM Sites validation failed")
        print("------------------------------------")
        print_validation_messages(messages)
        log_validation_failed("Recovery ZVM Sites", messages, excel_file)
        validations["recovery_zvm_sites"] = validation_failed(
            messages,
            error.errors(include_url=False),
        )
        raw_log(
            "validation.recovery_zvm_sites",
            validations["recovery_zvm_sites"],
        )
        stop_after_validation_failure("Recovery ZVM Sites")
        return

    log_validation_started("VPGs")
    logging.info("Resolving inherited and default VPG values")
    try:
        result = validate_vpgs(vpgs, vpg_settings, recovery_zvm_sites)
        validations["vpgs"] = validation_passed(result)
        raw_log("validation.vpgs", validations["vpgs"])
        print("\nVPGs validation passed")
        print("----------------------")
        log_validation_passed("VPGs")

    except WorkbookValidationError as error:
        print("\nVPGs validation failed")
        print("----------------------")
        print_validation_messages(error.messages)
        log_validation_failed("VPGs", error.messages, excel_file)
        validations["vpgs"] = validation_failed(error.messages)
        raw_log("validation.vpgs", validations["vpgs"])
        stop_after_validation_failure("VPGs")
        return

    except ValidationError as error:
        messages = format_validation_errors(error)
        print("\nVPGs validation failed")
        print("----------------------")
        print_validation_messages(messages)
        log_validation_failed("VPGs", messages, excel_file)
        validations["vpgs"] = validation_failed(
            messages,
            error.errors(include_url=False),
        )
        raw_log("validation.vpgs", validations["vpgs"])
        stop_after_validation_failure("VPGs")
        return

    log_validation_started("VM Replication")
    try:
        result = validate_vm_replication(vm_replication)
        validations["vm_replication"] = validation_passed(result)
        raw_log("validation.vm_replication", validations["vm_replication"])
        print("\nVM Replication validation passed")
        print("--------------------------------")
        log_validation_passed("VM Replication")

    except WorkbookValidationError as error:
        print("\nVM Replication validation failed")
        print("--------------------------------")
        print_validation_messages(error.messages)
        log_validation_failed("VM Replication", error.messages, excel_file)
        validations["vm_replication"] = validation_failed(error.messages)
        raw_log("validation.vm_replication", validations["vm_replication"])
        stop_after_validation_failure("VM Replication")
        return

    except ValidationError as error:
        messages = format_validation_errors(error)
        print("\nVM Replication validation failed")
        print("--------------------------------")
        print_validation_messages(messages)
        log_validation_failed("VM Replication", messages, excel_file)
        validations["vm_replication"] = validation_failed(
            messages,
            error.errors(include_url=False),
        )
        raw_log("validation.vm_replication", validations["vm_replication"])
        stop_after_validation_failure("VM Replication")
        return

    log_validation_started("VM Storage")
    try:
        result = validate_vm_storage(vm_storage)
        validations["vm_storage"] = validation_passed(result)
        raw_log("validation.vm_storage", validations["vm_storage"])
        print("\nVM Storage validation passed")
        print("----------------------------")
        log_validation_passed("VM Storage")

    except WorkbookValidationError as error:
        print("\nVM Storage validation failed")
        print("----------------------------")
        print_validation_messages(error.messages)
        log_validation_failed("VM Storage", error.messages, excel_file)
        validations["vm_storage"] = validation_failed(error.messages)
        raw_log("validation.vm_storage", validations["vm_storage"])
        stop_after_validation_failure("VM Storage")
        return

    except ValidationError as error:
        messages = format_validation_errors(error)
        print("\nVM Storage validation failed")
        print("----------------------------")
        print_validation_messages(messages)
        log_validation_failed("VM Storage", messages, excel_file)
        validations["vm_storage"] = validation_failed(
            messages,
            error.errors(include_url=False),
        )
        raw_log("validation.vm_storage", validations["vm_storage"])
        stop_after_validation_failure("VM Storage")
        return

    log_validation_started("VM NICs")
    try:
        result = validate_vm_nics(
            vm_nics,
            vpg_settings,
            recovery_zvm_sites,
            vpgs,
        )
        validations["vm_nics"] = validation_passed(result)
        raw_log("validation.vm_nics", validations["vm_nics"])
        print("\nVM NICs validation passed")
        print("-------------------------")
        log_validation_passed("VM NICs")

    except WorkbookValidationError as error:
        print("\nVM NICs validation failed")
        print("-------------------------")
        print_validation_messages(error.messages)
        log_validation_failed("VM NICs", error.messages, excel_file)
        validations["vm_nics"] = validation_failed(error.messages)
        raw_log("validation.vm_nics", validations["vm_nics"])
        stop_after_validation_failure("VM NICs")
        return

    except ValidationError as error:
        messages = format_validation_errors(error)
        print("\nVM NICs validation failed")
        print("-------------------------")
        print_validation_messages(messages)
        log_validation_failed("VM NICs", messages, excel_file)
        validations["vm_nics"] = validation_failed(
            messages,
            error.errors(include_url=False),
        )
        raw_log("validation.vm_nics", validations["vm_nics"])
        stop_after_validation_failure("VM NICs")
        return

    logging.info("Generating JSON output")
    log_validation_started("VCA Run manifest")
    try:
        output_path = write_zerto_json_dump(
            excel_file=excel_file,
            zerto_data=zerto_data,
            hypervisor_data=hypervisor_data,
            default_vpg_settings=vpg_settings,
            recovery_zvm_sites=recovery_zvm_sites,
            vpgs=vpgs,
            vm_replication=vm_replication,
            vm_storage=vm_storage,
            vm_nics=vm_nics,
            extended_journal=extended_journal,
            validations=validations,
        )
        site_settings_path = write_site_settings_json(site_settings, excel_file)
    except ManifestValidationError as error:
        print("\nVCA Run manifest validation failed")
        print("----------------------------------")
        print_manifest_validation_messages(error.messages)
        log_validation_failed("VCA Run manifest", error.messages, excel_file)
        raw_log("validation.vca_run_manifest", {
            "status": "failed",
            "errors": error.messages,
        })
        return

    raw_log("outputs", {
        "diagnostic_output_file": str(output_path),
        "manifest_output_file": str(manifest_output_path),
        "site_settings_file": str(site_settings_path),
    })
    print(f"\nDiagnostic dump written to {output_path}")
    print(f"VCA Run manifest written to {manifest_output_path}")
    print(f"Site Settings written to {site_settings_path}")
    logging.info("JSON output written to %s", output_path)
    logging.info("VCA Run manifest written to %s", manifest_output_path)
    logging.info("Site Settings written to %s", site_settings_path)
    logging.info("Run complete")


def print_zerto_summary(summary: dict) -> None:
    print("\nZerto Data Summary")
    print("------------------")

    print_topic_heading("ZVM Sites")
    for index, site in enumerate(summary["zvm_sites"]):
        if index > 0:
            print()
        print(f"- Site Name: {site['site_name']}")
        print(f"  Protected: {site['protected']}")
        print(f"  Recovery: {site['recovery']}")

    print_topic_heading("Labels")
    print_named_list("Scopes", summary["labels"]["scopes"])
    print_named_list("Waves", summary["labels"]["waves"])
    print_named_list("Application Names", summary["labels"]["application_names"])
    print_named_list(
        "Application Environments",
        summary["labels"]["application_environments"],
    )
    print_named_list("Data Types", summary["labels"]["data_types"])

    print_topic_heading("Recovery Scripts")
    for script in summary["recovery_scripts"]:
        print(f"- {script}")

    print_topic_heading("Boot Order Groups")
    for index, group in enumerate(summary["boot_order_groups"]):
        if index > 0:
            print()
        print(f"- Meta Group: {group['meta_group_name']}")
        print(f"  Group ID: {group['group_id']}")
        print(f"  Group Name: {group['group_name']}")
        print(f"  Boot Delay: {group['boot_delay_secs']} seconds")


def print_hypervisor_summary(hypervisor_data: dict) -> None:
    print("\nHypervisor Data Summary")
    print("-----------------------")

    print_topic_heading("Protected VMs")
    for index, vm in enumerate(hypervisor_data["protected_vms"]):
        if index > 0:
            print()
        print(f"- Site: {vm.get('Protected ZVM Site Name')}")
        print(f"  VM Name: {vm.get('VM Name')}")
        print(f"  CPU Count: {vm.get('CPU Count')}")
        print(f"  Memory: {vm.get('Memory (GiB)')} GiB")

    print_topic_heading("Protected VM Volumes")
    for index, volume in enumerate(hypervisor_data["protected_vm_volumes"]):
        if index > 0:
            print()
        print(f"- VM: {volume.get('Protected ZVM Site Name')} | {volume.get('VM Name')}")
        print(f"  Volume: {volume.get('Volume Location')}")
        print(f"  Size: {volume.get('Provisioned Size (GiB)')} GiB")

    print_topic_heading("Protected VM NICs")
    for index, nic in enumerate(hypervisor_data["protected_vm_nics"]):
        if index > 0:
            print()
        print(f"- VM: {nic.get('Protected ZVM Site Name')} | {nic.get('VM Name')}")
        print(f"  NIC: {nic.get('NIC Name')}")
        print(f"  Network: {nic.get('Network Name')}")

    print_topic_heading("Recovery Hosts")
    for index, host in enumerate(hypervisor_data["recovery_hosts"]):
        if index > 0:
            print()
        print(f"- Site: {host.get('Recovery ZVM Site Name')}")
        print(f"  Host: {host.get('Host Name')}")

    print_topic_heading("Recovery Datastores")
    for index, datastore in enumerate(hypervisor_data["recovery_datastores"]):
        if index > 0:
            print()
        print(f"- Site: {datastore.get('Recovery ZVM Site Name')}")
        print(f"  Datastore: {datastore.get('Datastore Name')}")
        print(f"  Size: {datastore.get('Size (GiB)')} GiB")

    print_topic_heading("Recovery Folders")
    for index, folder in enumerate(hypervisor_data["recovery_folders"]):
        if index > 0:
            print()
        print(f"- Site: {folder.get('Recovery ZVM Site Name')}")
        print(f"  Folder: {folder.get('Folder Name')}")

    print_topic_heading("Recovery Networks")
    for index, network in enumerate(hypervisor_data["recovery_networks"]):
        if index > 0:
            print()
        print(f"- Site: {network.get('Recovery ZVM Site Name')}")
        print(f"  Network: {network.get('Network Name')}")


def print_topic_heading(title: str) -> None:
    print(f"\n{title}\n")


def log_extraction_summary(
    zerto_data: dict,
    hypervisor_data: dict,
    recovery_zvm_sites: list,
    vpgs: list,
    vm_replication: list,
    vm_storage: list,
    vm_nics: list,
) -> None:
    logging.info("Extraction complete")
    logging.info(
        "Zerto Data: %s sites, %s recovery scripts, %s boot order groups",
        len(zerto_data["summary"]["zvm_sites"]),
        len(zerto_data["summary"]["recovery_scripts"]),
        len(zerto_data["summary"]["boot_order_groups"]),
    )
    logging.info(
        "Hypervisor Data: %s protected VMs, %s volumes, %s NICs, "
        "%s recovery hosts, %s datastores, %s folders, %s networks",
        len(hypervisor_data["protected_vms"]),
        len(hypervisor_data["protected_vm_volumes"]),
        len(hypervisor_data["protected_vm_nics"]),
        len(hypervisor_data["recovery_hosts"]),
        len(hypervisor_data["recovery_datastores"]),
        len(hypervisor_data["recovery_folders"]),
        len(hypervisor_data["recovery_networks"]),
    )
    logging.info("Recovery ZVM Sites rows: %s", len(recovery_zvm_sites))
    logging.info("VPG rows: %s", len(vpgs))
    logging.info("VM Replication rows: %s", len(vm_replication))
    logging.info("VM Storage rows: %s", len(vm_storage))
    logging.info("VM NIC rows: %s", len(vm_nics))


def log_validation_passed(section_name: str) -> None:
    logging.info("%s validation passed", section_name)


def log_validation_started(section_name: str) -> None:
    logging.info("Validating %s", section_name)


def log_validation_failed(
    section_name: str,
    messages: list[str],
    excel_file: str | Path,
) -> None:
    error_path = write_validation_errors(section_name, messages, excel_file)
    print(f"\nValidation error report written to {error_path}")

    logging.error("%s validation failed with %s error(s)", section_name, len(messages))

    for message in messages:
        logging.error("%s validation error:\n%s", section_name, message)

    logging.info("Validation error report written to %s", error_path)


def print_named_list(label: str, values: list) -> None:
    print(f"- {label}:")

    if not values:
        print("  Not set")
        print()
        return

    for value in values:
        print(f"  - {value}")

    print()


def print_validation_messages(messages: list[str]) -> None:
    for index, message in enumerate(messages):
        if index > 0:
            print()
        print(f"- {message}")


def print_manifest_validation_messages(messages: list[str]) -> None:
    grouped_messages = {}

    for message in messages:
        vpg_name = extract_manifest_error_vpg_name(message)
        grouped_messages.setdefault(vpg_name, []).append(message)

    for index, (vpg_name, vpg_messages) in enumerate(grouped_messages.items()):
        if index > 0:
            print()

        print(f"VPG: {vpg_name}")
        for message in vpg_messages:
            print(f"- {strip_manifest_error_vpg_name(message, vpg_name)}")


def extract_manifest_error_vpg_name(message: str) -> str:
    marker = "VPG '"
    start = message.find(marker)
    if start == -1:
        return "<unknown VPG>"

    start += len(marker)
    end = message.find("'", start)
    if end == -1:
        return "<unknown VPG>"

    return message[start:end]


def strip_manifest_error_vpg_name(message: str, vpg_name: str) -> str:
    return message.replace(f" for VPG '{vpg_name}', ", " for ", 1)


def stop_after_validation_failure(section_name: str) -> None:
    message = (
        f"Stopping validation because {section_name} failed. "
        "Fix this section and run VCA Check again."
    )
    print(f"\n{message}")
    raw_log("run_stopped", {
        "failed_section": section_name,
        "reason": "Validation failed; later sheets were not validated.",
    })


def validation_passed(result) -> dict:
    return {
        "status": "passed",
        "records": make_json_safe(result),
    }


def validation_failed(messages: list[str], errors: list | None = None) -> dict:
    return {
        "status": "failed",
        "messages": messages,
        "errors": errors or [],
    }


def print_hypervisor_validation(data: dict) -> None:
    print_key_values({
        "Protected VMs": len(data["protected_vms"]),
        "Protected VM Volumes": len(data["protected_vm_volumes"]),
        "Protected VM NICs": len(data["protected_vm_nics"]),
        "Recovery Hosts": len(data["recovery_hosts"]),
        "Recovery Datastores": len(data["recovery_datastores"]),
        "Recovery Folders": len(data["recovery_folders"]),
        "Recovery Networks": len(data["recovery_networks"]),
    })


def print_default_vpg_settings_validation(settings) -> None:
    rows = {
        "Protected Site": settings.protected_site,
        "Recovery Site": settings.recovery_site,
        "VPG Type": settings.vpg_type,
        "Priority": settings.priority,
        "Journal History": format_value_unit(settings.journal_history),
        "Target RPO Alert": format_value_unit(settings.target_rpo_alert),
        "Test Reminder": settings.test_reminder,
        "Journal Size Hard Limit": format_value_unit(settings.journal_size_hard_limit),
        "Journal Size Warning": format_value_unit(settings.journal_size_warning),
        "Scratch Journal Size Hard Limit": format_value_unit(
            settings.scratch_journal_size_hard_limit,
        ),
        "Scratch Journal Size Warning": format_value_unit(
            settings.scratch_journal_size_warning,
        ),
        "WAN Compression": settings.wan_compression,
    }

    print_key_values(rows)


def print_recovery_zvm_sites_validation(sites: list) -> None:
    for index, site in enumerate(sites, start=1):
        print(f"\nRecovery ZVM Site #{index}")
        print_key_values({
            "Recovery ZVM Site Name": site.recovery_zvm_site_name,
            "VPG Type": site.vpg_type,
            "Priority": site.priority,
            "Recovery Host Name": site.recovery_host_name,
            "Recovery Datastore Name": site.recovery_datastore_name,
            "Journal History": format_optional_value_unit(
                site.journal_history_value,
                site.journal_history_unit,
            ),
            "Target RPO Alert": format_optional_value_unit(
                site.target_rpo_alert_value,
                site.target_rpo_alert_unit,
            ),
            "Test Reminder": site.test_reminder,
            "Journal Datastore Name": site.journal_datastore_name,
            "Journal Size Hard Limit": format_optional_value_unit(
                site.journal_size_hard_limit_value,
                site.journal_size_hard_limit_unit,
            ),
            "Journal Size Warning Threshold": format_optional_value_unit(
                site.journal_size_warning_threshold_value,
                site.journal_size_warning_threshold_unit,
            ),
            "Scratch Journal Datastore Name": site.scratch_journal_datastore_name,
            "Scratch Journal Size Hard Limit": format_optional_value_unit(
                site.scratch_journal_size_hard_limit_value,
                site.scratch_journal_size_hard_limit_unit,
            ),
            "Scratch Journal Size Warning Threshold": format_optional_value_unit(
                site.scratch_journal_size_warning_threshold_value,
                site.scratch_journal_size_warning_threshold_unit,
            ),
            "Enable WAN Traffic Compression": site.enable_wan_traffic_compression,
            "Disk Provisioning Override": site.disk_provisioning_override,
            "Failover Live / Move Network Name": site.failover_live_move_network_name,
            "Failover Test Network Name": site.failover_test_network_name,
            "Recovery Folder Name": site.recovery_folder_name,
            "Pre-Recovery Script Name": site.pre_recovery_script_name,
            "Pre-Recovery Script Parameters": site.pre_recovery_script_parameters,
            "Pre-Recovery Script Execution Timeout (Seconds)": (
                site.pre_recovery_script_execution_timeout_seconds
            ),
            "Post-Recovery Script Name": site.post_recovery_script_name,
            "Post-Recovery Script Parameters": site.post_recovery_script_parameters,
            "Post-Recovery Script Execution Timeout (Seconds)": (
                site.post_recovery_script_execution_timeout_seconds
            ),
            "Failover Live / Move - Create new MAC address": (
                site.failover_live_move_create_new_mac_address
            ),
            "Failover Live / Move - Change vNIC IP Config": (
                site.failover_live_move_change_vnic_ip_config
            ),
            "Failover Live / Move - Subnet Mask": site.failover_live_move_subnet_mask,
            "Failover Live / Move - Default Gateway": (
                site.failover_live_move_default_gateway
            ),
            "Failover Live / Move - Preferred DNS Server": (
                site.failover_live_move_preferred_dns_server
            ),
            "Failover Live / Move - Alternate DNS Server": (
                site.failover_live_move_alternate_dns_server
            ),
            "Failover Live / Move - DNS Suffix": site.failover_live_move_dns_suffix,
            "Failover Test - Create new MAC address": (
                site.failover_test_create_new_mac_address
            ),
            "Failover Test - Change vNIC IP Config": (
                site.failover_test_change_vnic_ip_config
            ),
            "Failover Test - Subnet Mask": site.failover_test_subnet_mask,
            "Failover Test - Default Gateway": site.failover_test_default_gateway,
            "Failover Test - Preferred DNS Server": (
                site.failover_test_preferred_dns_server
            ),
            "Failover Test - Alternate DNS Server": (
                site.failover_test_alternate_dns_server
            ),
            "Failover Test - DNS Suffix": site.failover_test_dns_suffix,
        })


def print_vpgs_validation(vpgs: list) -> None:
    for index, vpg in enumerate(vpgs, start=1):
        print(f"\nVPG #{index}")
        print_key_values({
            "VPG Name": vpg.vpg_name,
            "Protected ZVM Site Name": vpg.protected_zvm_site_name,
            "Recovery ZVM Site Name": vpg.recovery_zvm_site_name,
            "VPG Type": vpg.vpg_type,
            "Priority": vpg.priority,
            "VPG Description": vpg.vpg_description,
            "Label 1": vpg.label_1,
            "Label 2": vpg.label_2,
            "Label 3": vpg.label_3,
            "Label 4": vpg.label_4,
            "Label 5": vpg.label_5,
            "Boot Order Meta Group Name": vpg.boot_order_meta_group_name,
            "Recovery Host Name": vpg.recovery_host_name,
            "Recovery Datastore Name": vpg.recovery_datastore_name,
            "Journal History": format_optional_value_unit(
                vpg.journal_history_value,
                vpg.journal_history_unit,
            ),
            "Target RPO Alert": format_optional_value_unit(
                vpg.target_rpo_alert_value,
                vpg.target_rpo_alert_unit,
            ),
            "Test Reminder": vpg.test_reminder,
            "Journal Datastore Name": vpg.journal_datastore_name,
            "Journal Size Hard Limit": format_optional_value_unit(
                vpg.journal_size_hard_limit_value,
                vpg.journal_size_hard_limit_unit,
            ),
            "Journal Size Warning Threshold": format_optional_value_unit(
                vpg.journal_size_warning_threshold_value,
                vpg.journal_size_warning_threshold_unit,
            ),
            "Scratch Journal Datastore Name": vpg.scratch_journal_datastore_name,
            "Scratch Journal Size Hard Limit": format_optional_value_unit(
                vpg.scratch_journal_size_hard_limit_value,
                vpg.scratch_journal_size_hard_limit_unit,
            ),
            "Scratch Journal Size Warning Threshold": format_optional_value_unit(
                vpg.scratch_journal_size_warning_threshold_value,
                vpg.scratch_journal_size_warning_threshold_unit,
            ),
            "Enable WAN Traffic Compression": vpg.enable_wan_traffic_compression,
            "Disk Provisioning Override": vpg.disk_provisioning_override,
            "Failover Live / Move - Network Name": (
                vpg.failover_live_move_network_name
            ),
            "Failover Test Network Name": vpg.failover_test_network_name,
            "Recovery Folder Name": vpg.recovery_folder_name,
            "Pre-Recovery Script Name": vpg.pre_recovery_script_name,
            "Pre-Recovery Script Parameters": vpg.pre_recovery_script_parameters,
            "Pre-Recovery Script Execution Timeout (Seconds)": (
                vpg.pre_recovery_script_execution_timeout_seconds
            ),
            "Post-Recovery Script Name": vpg.post_recovery_script_name,
            "Post-Recovery Script Parameters": vpg.post_recovery_script_parameters,
            "Post-Recovery Script Execution Timeout (Seconds)": (
                vpg.post_recovery_script_execution_timeout_seconds
            ),
        })


def print_vm_replication_validation(rows: list) -> None:
    for index, row in enumerate(rows, start=1):
        print(f"\nVM Replication Row #{index}")
        print_key_values({
            "VPG Name": row.vpg_name,
            "VM Name": row.vm_name,
            "Label 1": row.label_1,
            "Label 2": row.label_2,
            "Label 3": row.label_3,
            "Label 4": row.label_4,
            "Label 5": row.label_5,
            "Boot Order Group Name": row.boot_order_group_name,
            "Recovery Host Name": row.recovery_host_name,
            "Recovery Datastore Name": row.recovery_datastore_name,
            "Recovery Folder Name": row.recovery_folder_name,
            "Journal Datastore Name": row.journal_datastore_name,
            "Journal Size Hard Limit": format_optional_value_unit(
                row.journal_size_hard_limit_value,
                row.journal_size_hard_limit_unit,
            ),
            "Journal Size Warning Threshold": format_optional_value_unit(
                row.journal_size_warning_threshold_value,
                row.journal_size_warning_threshold_unit,
            ),
            "Scratch Journal Datastore Name": row.scratch_journal_datastore_name,
            "Scratch Journal Size Hard Limit": format_optional_value_unit(
                row.scratch_journal_size_hard_limit_value,
                row.scratch_journal_size_hard_limit_unit,
            ),
            "Scratch Journal Size Warning Threshold": format_optional_value_unit(
                row.scratch_journal_size_warning_threshold_value,
                row.scratch_journal_size_warning_threshold_unit,
            ),
        })


def print_vm_storage_validation(rows: list) -> None:
    for index, row in enumerate(rows, start=1):
        print(f"\nVM Storage Row #{index}")
        print_key_values({
            "VPG Name": row.vpg_name,
            "VM Name": row.vm_name,
            "Protected Volume Location": row.protected_volume_location,
            "Size (GiB)": row.size_gib,
            "Recovery Volume Location": row.recovery_volume_location,
            "Recovery Raw Device Name": row.recovery_raw_device_name,
            "Disk Provisioning Override": row.disk_provisioning_override,
            "Volume Sync Type": row.volume_sync_type,
        })


def print_vm_nics_validation(rows: list) -> None:
    for index, row in enumerate(rows, start=1):
        print(f"\nVM NICs Row #{index}")
        print_key_values({
            "VPG Name": row.vpg_name,
            "VM Name": row.vm_name,
            "NIC Name": row.nic_name,
            "Protected Network Name": row.protected_network_name,
            "Failover Live / Move - Network Name": (
                row.failover_live_move_network_name
            ),
            "Failover Live / Move - Create new MAC address": (
                row.failover_live_move_create_new_mac_address
            ),
            "Failover Live / Move - Change vNIC IP Config": (
                row.failover_live_move_change_vnic_ip_config
            ),
            "Failover Live / Move - IP Address": row.failover_live_move_ip_address,
            "Failover Live / Move - Subnet Mask": row.failover_live_move_subnet_mask,
            "Failover Live / Move - Default Gateway": (
                row.failover_live_move_default_gateway
            ),
            "Failover Live / Move - Preferred DNS Server": (
                row.failover_live_move_preferred_dns_server
            ),
            "Failover Live / Move - Alternate DNS Server": (
                row.failover_live_move_alternate_dns_server
            ),
            "Failover Live / Move - DNS Suffix": row.failover_live_move_dns_suffix,
            "Failover Test - Network Name": row.failover_test_network_name,
            "Failover Test - Create new MAC address": (
                row.failover_test_create_new_mac_address
            ),
            "Failover Test - Change vNIC IP Config": (
                row.failover_test_change_vnic_ip_config
            ),
            "Failover Test - IP Address": row.failover_test_ip_address,
            "Failover Test - Subnet Mask": row.failover_test_subnet_mask,
            "Failover Test - Default Gateway": row.failover_test_default_gateway,
            "Failover Test - Preferred DNS Server": (
                row.failover_test_preferred_dns_server
            ),
            "Failover Test - Alternate DNS Server": (
                row.failover_test_alternate_dns_server
            ),
            "Failover Test - DNS Suffix": row.failover_test_dns_suffix,
        })


def print_key_values(rows: dict) -> None:
    for label, value in rows.items():
        print(f"- {label}: {format_display_value(value)}")


def format_value_unit(value_unit) -> str:
    return f"{value_unit.value:g} {value_unit.unit}"


def format_optional_value_unit(value, unit) -> str | None:
    if value is None and unit is None:
        return None

    if value is None:
        return unit

    if unit is None:
        return str(value)

    return f"{value:g} {unit}"


def format_display_value(value) -> str:
    if value is None:
        return "Not set"

    return str(value)


if __name__ == "__main__":
    try:
        arguments = parse_args()
        main(arguments.input_file)
    except Exception:
        raw_log("unhandled_exception", traceback.format_exc())
        raise
