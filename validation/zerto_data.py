from collections import Counter

from validation.error_formatting import WorkbookValidationError, format_workbook_error


YES_NO_VALUES = ("Yes", "No")
ZERTO_VERSION_VALUES = ("10.9.x", "10.8.x", "10.0U7.x")
LABEL_TABLES = {
    "Label 1": "Zerto_Data_Label_1",
    "Label 2": "Zerto_Data_Label_2",
    "Label 3": "Zerto_Data_Label_3",
    "Label 4": "Zerto_Data_Label_4",
    "Label 5": "Zerto_Data_Label_5",
}
TABLE_ID_COLUMNS = {
    "Zerto_Data_ZVM_Site_Names": "ID",
    "Zerto_Data_Label_1": "ID.1",
    "Zerto_Data_Label_2": "ID.2",
    "Zerto_Data_Label_3": "ID.3",
    "Zerto_Data_Label_4": "ID.4",
    "Zerto_Data_Label_5": "ID.5",
    "Zerto_Data_Recovery_Scripts": "ID.6",
    "Zerto_Data_Boot_Order_Groups": "ID.7",
}
BOOT_ORDER_GROUP_REQUIRED_COLUMNS = (
    ("ID.7", "ID"),
    ("Group ID", "Group ID"),
    ("Meta Group Name", "Meta Group Name"),
    ("Group Name", "Group Name"),
    ("Boot Delay (Secs)", "Boot Delay (Secs)"),
)


def validate_zerto_data(zerto_data: dict) -> dict:
    records = zerto_data["records"]
    messages = []

    messages.extend(validate_zvm_sites(records))
    messages.extend(validate_labels(records))
    messages.extend(validate_recovery_scripts(records))
    messages.extend(validate_boot_order_groups(records))

    if messages:
        raise WorkbookValidationError(messages)

    return zerto_data["summary"]


def validate_zvm_sites(records: list[dict]) -> list[str]:
    messages = []
    zvm_site_rows = [
        row
        for row in records
        if any(
            row.get(column) is not None
            for column in ("ZVM Site Name", "Zerto Version", "Protected?", "Recovery?")
        )
    ]

    messages.extend(validate_unique_values(
        zvm_site_rows,
        "ZVM Site Name",
        "Zerto_Data_ZVM_Site_Names",
    ))

    for row in zvm_site_rows:
        for column_name in ("Protected?", "Recovery?"):
            value = row.get(column_name)
            if value is None or value in YES_NO_VALUES:
                continue

            messages.append(build_error(
                row,
                "Zerto_Data_ZVM_Site_Names",
                column_name,
                value,
                f"Valid values are: {', '.join(repr(value) for value in YES_NO_VALUES)}",
            ))

        protected = row.get("Protected?")
        recovery = row.get("Recovery?")

        if (
            row.get("ZVM Site Name")
            and protected != "Yes"
            and recovery != "Yes"
        ):
            messages.append(build_error(
                row,
                "Zerto_Data_ZVM_Site_Names",
                "Protected? / Recovery?",
                f"{protected or 'blank'} / {recovery or 'blank'}",
                "At least one value must be 'Yes'.",
            ))

        zerto_version = row.get("Zerto Version")
        if zerto_version is None:
            messages.append(build_error(
                row,
                "Zerto_Data_ZVM_Site_Names",
                "Zerto Version",
                None,
                "This value is mandatory.",
            ))
        elif str(zerto_version) not in ZERTO_VERSION_VALUES:
            valid_values = ", ".join(repr(value) for value in ZERTO_VERSION_VALUES)
            messages.append(build_error(
                row,
                "Zerto_Data_ZVM_Site_Names",
                "Zerto Version",
                zerto_version,
                f"Valid values are: {valid_values}.",
            ))

    return messages


def validate_labels(records: list[dict]) -> list[str]:
    messages = []

    for column_name, table_name in LABEL_TABLES.items():
        messages.extend(validate_unique_values(records, column_name, table_name))

    return messages


def validate_recovery_scripts(records: list[dict]) -> list[str]:
    return validate_unique_values(
        records,
        "Recovery Script Name",
        "Zerto_Data_Recovery_Scripts",
    )


def validate_boot_order_groups(records: list[dict]) -> list[str]:
    messages = []
    boot_order_rows = [
        row
        for row in records
        if any(
            row.get(column) is not None
            for column, _ in BOOT_ORDER_GROUP_REQUIRED_COLUMNS
        )
    ]

    for row in boot_order_rows:
        for column_name, display_name in BOOT_ORDER_GROUP_REQUIRED_COLUMNS:
            if row.get(column_name) is not None:
                continue

            messages.append(build_error(
                row,
                "Zerto_Data_Boot_Order_Groups",
                display_name,
                None,
                "This value is mandatory.",
            ))

    messages.extend(validate_unique_combinations(
        boot_order_rows,
        ("Meta Group Name", "Group Name"),
        "Zerto_Data_Boot_Order_Groups",
        "Group Name",
    ))

    for row in boot_order_rows:
        boot_delay = row.get("Boot Delay (Secs)")
        if boot_delay is None:
            continue

        if not is_number_between(boot_delay, 1, 999):
            messages.append(build_error(
                row,
                "Zerto_Data_Boot_Order_Groups",
                "Boot Delay (Secs)",
                boot_delay,
                "Valid range is: 1-999.",
            ))

    return messages


def validate_unique_values(
    rows: list[dict],
    column_name: str,
    table_name: str,
) -> list[str]:
    values = [
        row.get(column_name)
        for row in rows
        if row.get(column_name) is not None
    ]
    duplicate_values = {
        value
        for value, count in Counter(values).items()
        if count > 1
    }

    return [
        build_error(
            row,
            table_name,
            column_name,
            row.get(column_name),
            "Value must be unique.",
        )
        for row in rows
        if row.get(column_name) in duplicate_values
    ]


def validate_unique_combinations(
    rows: list[dict],
    column_names: tuple[str, ...],
    table_name: str,
    error_column_name: str,
) -> list[str]:
    keys = [
        tuple(row.get(column_name) for column_name in column_names)
        for row in rows
        if all(row.get(column_name) is not None for column_name in column_names)
    ]
    duplicate_keys = {
        key
        for key, count in Counter(keys).items()
        if count > 1
    }

    return [
        build_error(
            row,
            table_name,
            error_column_name,
            row.get(error_column_name),
            f"Combination must be unique: {', '.join(column_names)}.",
        )
        for row in rows
        if tuple(row.get(column_name) for column_name in column_names) in duplicate_keys
    ]


def is_number_between(value, minimum: int, maximum: int) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False

    return minimum <= number <= maximum


def build_error(
    row: dict,
    table_name: str,
    column_name: str,
    input_value,
    error_message: str,
) -> str:
    row_context = {
        "__sheet_name": row.get("__sheet_name", "Zerto Data"),
        "__table_name": table_name,
        "__excel_row": row.get("__excel_row", "Unknown"),
        "__table_row_id": get_table_row_id(row, table_name),
    }

    return format_workbook_error(
        row_context,
        column_name,
        input_value,
        error_message,
    )


def get_table_row_id(row: dict, table_name: str):
    id_column = TABLE_ID_COLUMNS.get(table_name, "ID")
    return row.get(id_column) or row.get("__table_row_id", "Unknown")
