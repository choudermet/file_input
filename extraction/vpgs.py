import config
from extraction.tables import extract_sheet_table


def extract_vpgs(excel_file: str) -> list[dict]:
    vpgs = extract_sheet_table(
        excel_file,
        "VPGs",
        "VPG Name",
        table_name="VPGs",
    )
    load_vpgs_into_config(vpgs)
    return vpgs


def load_vpgs_into_config(vpgs: list[dict]) -> None:
    config.vpg_names = [
        vpg["VPG Name"]
        for vpg in vpgs
        if vpg.get("VPG Name")
    ]
    config.vpg_protected_site_names_by_vpg_name = {
        vpg["VPG Name"]: vpg.get("Protected ZVM Site Name")
        for vpg in vpgs
        if vpg.get("VPG Name")
    }
    config.vpg_recovery_site_names_by_vpg_name = {
        vpg["VPG Name"]: vpg.get("Recovery ZVM Site Name")
        for vpg in vpgs
        if vpg.get("VPG Name")
    }
    config.vpg_boot_order_meta_group_names_by_vpg_name = {
        vpg["VPG Name"]: vpg.get("Boot Order Meta Group Name")
        for vpg in vpgs
        if vpg.get("VPG Name")
    }
