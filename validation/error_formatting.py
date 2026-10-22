from ast import literal_eval

from pydantic import ValidationError


FIELD_LABELS = {
    "protected_site": "Protected Site",
    "recovery_site": "Recovery Site",
    "vpg_type": "VPG Type",
    "priority": "Priority",
    "journal_history": "Journal History",
    "target_rpo_alert": "Target RPO Alert",
    "test_reminder": "Test Reminder",
    "journal_size_hard_limit": "Journal Size Hard Limit",
    "journal_size_warning": "Journal Size Warning Threshold",
    "scratch_journal_size_hard_limit": "Scratch Journal Size Hard Limit",
    "scratch_journal_size_warning": "Scratch Journal Size Warning Threshold",
    "wan_compression": "Enable WAN Traffic Compression",
    "disk_provisioning_override": "Disk Provisioning Override",
    "recovery_folder_name": "Recovery Folder Name",
    "volume_sync_type": "Volume Sync Type",
    "pre_recovery_script_execution_timeout_seconds": (
        "Pre-Recovery Script Execution Timeout (Seconds)"
    ),
    "post_recovery_script_execution_timeout_seconds": (
        "Post-Recovery Script Execution Timeout (Seconds)"
    ),
    "failover_live_move_create_new_mac_address": (
        "Failover Live / Move - Create new MAC address"
    ),
    "failover_test_create_new_mac_address": (
        "Failover Test - Create new MAC address"
    ),
    "failover_live_move_change_vnic_ip_config": (
        "Failover Live / Move - Change vNIC IP Config"
    ),
    "failover_test_change_vnic_ip_config": (
        "Failover Test - Change vNIC IP Config"
    ),
    "failover_live_move_subnet_mask": "Failover Live / Move - Subnet Mask",
    "failover_test_subnet_mask": "Failover Test - Subnet Mask",
    "failover_live_move_default_gateway": (
        "Failover Live / Move - Default Gateway"
    ),
    "failover_test_default_gateway": "Failover Test - Default Gateway",
    "failover_live_move_preferred_dns_server": (
        "Failover Live / Move - Preferred DNS Server"
    ),
    "failover_test_preferred_dns_server": (
        "Failover Test - Preferred DNS Server"
    ),
    "failover_live_move_alternate_dns_server": (
        "Failover Live / Move - Alternate DNS Server"
    ),
    "failover_test_alternate_dns_server": (
        "Failover Test - Alternate DNS Server"
    ),
    "failover_live_move_dns_suffix": "Failover Live / Move - DNS Suffix",
    "failover_test_dns_suffix": "Failover Test - DNS Suffix",
    "extended_journal_run_at": "Extended Journal - Run at (HH:MI)",
    "extended_journal_retry_count": (
        "Extended Journal - Number of automatic retry commands"
    ),
    "extended_journal_wait_between_retries_minutes": (
        "Extended Journal - Wait time between retries (minutes)"
    ),
}


class WorkbookValidationError(ValueError):
    def __init__(self, messages: list[str]):
        self.messages = messages
        super().__init__("\n".join(messages))


def validate_model_rows(model, rows: list[dict]) -> list:
    validated_rows = []
    messages = []

    for row in rows:
        try:
            validated_rows.append(model(**row))
        except ValidationError as error:
            messages.extend(format_validation_errors(error, row))

    if messages:
        raise WorkbookValidationError(messages)

    return validated_rows


def format_validation_errors(
    error: ValidationError,
    row_context: dict | None = None,
) -> list[str]:
    return [
        format_validation_error(error_detail, row_context)
        for error_detail in error.errors(include_url=False)
    ]


def format_validation_error(
    error_detail: dict,
    row_context: dict | None = None,
) -> str:
    column_name = format_location(error_detail.get("loc", []))
    input_value = error_detail.get("input")
    valid_values = get_valid_values(error_detail)
    valid_range = get_valid_range(error_detail)
    error_message = get_error_message(error_detail, valid_values, valid_range)
    column_name, input_value = refine_row_level_error(
        column_name,
        input_value,
        error_message,
    )

    if row_context:
        return format_workbook_error(
            row_context,
            column_name,
            input_value,
            error_message,
        )

    return (
        f"Input value {input_value!r} for '{column_name}' is not valid. "
        f"{error_message}"
    )


def refine_row_level_error(
    column_name: str,
    input_value,
    error_message: str,
) -> tuple[str, object]:
    if column_name or not isinstance(input_value, dict):
        return column_name, input_value

    paired_fields = {
        "Journal History Value and Unit must be provided together": (
            "Journal History Value / Journal History Unit",
            (
                "Journal History Value",
                "Journal History Unit",
            ),
        ),
        "Target RPO Alert Value and Unit must be provided together": (
            "Target RPO Alert Value / Target RPO Alert Unit",
            (
                "Target RPO Alert Value",
                "Target RPO Alert Unit",
            ),
        ),
    }
    if error_message not in paired_fields:
        return column_name, "row-level validation"

    display_name, field_names = paired_fields[error_message]
    return display_name, {
        field_name: input_value.get(field_name)
        for field_name in field_names
    }


def get_error_message(
    error_detail: dict,
    valid_values: str | None,
    valid_range: str | None,
) -> str:
    if valid_values:
        if valid_values == "EMPTY_ALLOWED_VALUES":
            return "Valid values are: []."

        return f"Valid values are: {valid_values}."

    if valid_range:
        return f"Valid range is: {valid_range}."

    message = error_detail.get("msg", "Please check the workbook value.")
    return message.removeprefix("Value error, ")


def format_workbook_error(
    row_context: dict,
    column_name: str,
    input_value,
    error_message: str,
) -> str:
    table_name = row_context.get("__table_name", "Unknown")
    table_row_id = row_context.get("__table_row_id", "Unknown")
    excel_row = row_context.get("__excel_row")

    worksheet_row = ""
    if excel_row is not None:
        worksheet_row = f"  Worksheet Row: {format_row_id(excel_row)}\n"

    return (
        f"Table: {table_name}\n"
        f"  Table Row ID: {format_row_id(table_row_id)}\n"
        f"{worksheet_row}"
        f"  Column: {column_name}\n"
        f"  Input value: {input_value!r}\n"
        f"  Error: {error_message}"
    )


def format_row_id(value) -> str:
    if value is None:
        return "blank"

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value)


def format_location(location) -> str:
    if isinstance(location, (list, tuple)):
        return " -> ".join(format_location_item(item) for item in location)

    return format_location_item(location)


def format_location_item(item) -> str:
    return FIELD_LABELS.get(str(item), str(item))


def get_valid_values(error_detail: dict) -> str | None:
    context = error_detail.get("ctx") or {}

    if "expected" in context:
        return context["expected"]

    error = context.get("error")
    if error is None:
        return None

    message = str(error)
    marker = "Allowed values"
    if marker not in message:
        return None

    allowed_values = message.split(marker, 1)[1].strip()
    if allowed_values.startswith(":"):
        allowed_values = allowed_values[1:].strip()

    return format_allowed_values(allowed_values)


def get_valid_range(error_detail: dict) -> str | None:
    context = error_detail.get("ctx") or {}
    minimum = context.get("ge")
    maximum = context.get("le")

    if minimum is not None and maximum is not None:
        return f"{minimum}-{maximum}"

    if minimum is not None:
        return f"{minimum} or greater"

    if maximum is not None:
        return f"{maximum} or lower"

    return None


def format_allowed_values(value: str) -> str:
    try:
        parsed_value = literal_eval(value)
    except (SyntaxError, ValueError):
        return value

    if isinstance(parsed_value, list):
        if not parsed_value:
            return "EMPTY_ALLOWED_VALUES"

        return ", ".join(repr(item) for item in parsed_value)

    return value
