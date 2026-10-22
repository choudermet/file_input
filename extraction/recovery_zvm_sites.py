from extraction.tables import extract_sheet_table


def extract_recovery_zvm_sites(excel_file: str) -> list[dict]:
    return extract_sheet_table(
        excel_file,
        sheet_name="Recovery ZVM Sites",
        required_header="Recovery ZVM Site Name",
        table_name="Recovery_ZVM_Sites",
    )
