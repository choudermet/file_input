import pandas as pd
import config
from extraction.tables import clean_records


def extract_hypervisor_data(excel_file: str) -> dict:
    raw_df = pd.read_excel(
        excel_file,
        sheet_name="Hypervisor Data",
        engine="openpyxl",
        header=None,
    )

    table_locations = find_table_locations(raw_df)
    header_row_index = find_header_row(raw_df, "Protected ZVM Site Name")

    tables = {
        "protected_vms": extract_named_table(
            raw_df,
            table_locations,
            header_row_index,
            "Hypervisor_Data_Protected_ZVM_VMs",
        ),
        "protected_vm_volumes": extract_named_table(
            raw_df,
            table_locations,
            header_row_index,
            "Hypervisor_Data_Protected_ZVM_VM_Volumes",
        ),
        "protected_vm_nics": extract_named_table(
            raw_df,
            table_locations,
            header_row_index,
            "Hypervisor_Data_Protected_ZVM_VM_NICs",
        ),
        "recovery_hosts": extract_named_table(
            raw_df,
            table_locations,
            header_row_index,
            "Hypervisor_Data_Recovery_ZVM_Hosts",
        ),
        "recovery_datastores": extract_named_table(
            raw_df,
            table_locations,
            header_row_index,
            "Hypervisor_Data_Recovery_ZVM_Datastores",
        ),
        "recovery_folders": extract_named_table(
            raw_df,
            table_locations,
            header_row_index,
            "Hypervisor_Data_Recovery_ZVM_Folders",
        ),
        "recovery_networks": extract_named_table(
            raw_df,
            table_locations,
            header_row_index,
            "Hypervisor_Data_Recovery_ZVM_Networks",
        ),
    }

    load_hypervisor_data_into_config(tables)

    return tables


def find_header_row(df: pd.DataFrame, required_text: str) -> int:
    for index, row in df.iterrows():
        values = [str(value).strip() for value in row.tolist() if pd.notna(value)]

        if required_text in values:
            return index

    raise ValueError(f"Could not find header row containing '{required_text}'")


def find_table_locations(raw_df: pd.DataFrame) -> dict[str, tuple[int, int]]:
    table_starts = []

    for _, row in raw_df.iterrows():
        values = row.tolist()

        for column_index, value in enumerate(values):
            if not isinstance(value, str):
                continue

            if not value.startswith("Hypervisor_Data_"):
                continue

            table_starts.append((value, max(column_index - 1, 0)))

        if table_starts:
            break

    if not table_starts:
        raise ValueError("Could not find Hypervisor Data table names")

    table_locations = {}
    max_column = raw_df.shape[1] - 1

    for index, (table_name, start_col) in enumerate(table_starts):
        if index + 1 < len(table_starts):
            end_col = table_starts[index + 1][1] - 1
        else:
            end_col = max_column

        table_locations[table_name] = (start_col, end_col)

    return table_locations


def extract_named_table(
    raw_df: pd.DataFrame,
    table_locations: dict[str, tuple[int, int]],
    header_row_index: int,
    table_name: str,
) -> list[dict]:
    if table_name not in table_locations:
        raise ValueError(f"Could not find Hypervisor Data table '{table_name}'")

    start_col, end_col = table_locations[table_name]
    return extract_table(
        raw_df,
        header_row_index,
        start_col,
        end_col,
        table_name=table_name,
    )


def extract_table(
    raw_df: pd.DataFrame,
    header_row_index: int,
    start_col: int,
    end_col: int,
    table_name: str | None = None,
) -> list[dict]:
    table_df = raw_df.iloc[header_row_index:, start_col:end_col + 1].copy()

    table_df.columns = table_df.iloc[0]
    table_df = table_df.iloc[1:]

    table_df = table_df.dropna(how="all")
    table_df = table_df.where(pd.notnull(table_df), None)

    records = []
    metadata = []

    for index, row in table_df.iterrows():
        records.append(row.to_dict())
        metadata.append({
            "__sheet_name": "Hypervisor Data",
            "__table_name": table_name,
            "__excel_row": index + 1,
        })

    return clean_records(records, metadata)


def load_hypervisor_data_into_config(tables: dict) -> None:
    config.protected_vms = tables["protected_vms"]
    config.protected_vm_volumes = tables["protected_vm_volumes"]
    config.protected_vm_nics = tables["protected_vm_nics"]

    config.recovery_hosts = tables["recovery_hosts"]
    config.recovery_datastores = tables["recovery_datastores"]
    config.recovery_folders = tables["recovery_folders"]
    config.recovery_networks = tables["recovery_networks"]

    config.protected_vm_names = [
        vm["VM Name"]
        for vm in config.protected_vms
        if vm.get("VM Name")
    ]
    config.protected_vm_names_by_site = {}
    for vm in config.protected_vms:
        site_name = vm.get("Protected ZVM Site Name")
        vm_name = vm.get("VM Name")

        if site_name and vm_name:
            config.protected_vm_names_by_site.setdefault(
                site_name,
                [],
            ).append(vm_name)

    config.protected_volume_locations_by_vm_name = {}
    config.protected_volume_locations_by_site_and_vm_name = {}
    for volume in config.protected_vm_volumes:
        site_name = volume.get("Protected ZVM Site Name")
        vm_name = volume.get("VM Name")
        volume_location = volume.get("Volume Location")

        if vm_name and volume_location:
            config.protected_volume_locations_by_vm_name.setdefault(
                vm_name,
                [],
            ).append(volume_location)

        if site_name and vm_name and volume_location:
            config.protected_volume_locations_by_site_and_vm_name.setdefault(
                (site_name, vm_name),
                [],
            ).append(volume_location)

    config.protected_nic_names_by_vm_name = {}
    config.protected_nic_names_by_site_and_vm_name = {}
    config.protected_network_names_by_vm_nic = {}
    config.protected_network_names_by_site_vm_nic = {}
    for nic in config.protected_vm_nics:
        site_name = nic.get("Protected ZVM Site Name")
        vm_name = nic.get("VM Name")
        nic_name = nic.get("NIC Name")
        network_name = nic.get("Network Name")

        if vm_name and nic_name:
            config.protected_nic_names_by_vm_name.setdefault(
                vm_name,
                [],
            ).append(nic_name)

        if site_name and vm_name and nic_name:
            config.protected_nic_names_by_site_and_vm_name.setdefault(
                (site_name, vm_name),
                [],
            ).append(nic_name)

        if vm_name and nic_name and network_name:
            config.protected_network_names_by_vm_nic[(vm_name, nic_name)] = network_name

        if site_name and vm_name and nic_name and network_name:
            config.protected_network_names_by_site_vm_nic[
                (site_name, vm_name, nic_name)
            ] = network_name

    config.recovery_host_names = [
        host["Host Name"]
        for host in config.recovery_hosts
        if host.get("Host Name")
    ]
    config.recovery_host_names_by_site = {}
    config.recovery_host_or_cluster_names_by_site = {}
    for host in config.recovery_hosts:
        site_name = host.get("Recovery ZVM Site Name")
        host_cluster_name = host.get("Host Cluster Name")
        host_name = host.get("Host Name")

        if site_name and host_name:
            config.recovery_host_names_by_site.setdefault(
                site_name,
                [],
            ).append(host_name)

        for value in (host_cluster_name, host_name):
            if not site_name or not value:
                continue

            site_values = config.recovery_host_or_cluster_names_by_site.setdefault(
                site_name,
                [],
            )
            if value not in site_values:
                site_values.append(value)

    config.recovery_datastore_names = [
        datastore["Datastore Name"]
        for datastore in config.recovery_datastores
        if datastore.get("Datastore Name")
    ]
    config.recovery_datastore_names_by_site = {}
    for datastore in config.recovery_datastores:
        site_name = datastore.get("Recovery ZVM Site Name")
        datastore_name = datastore.get("Datastore Name")

        if site_name and datastore_name:
            config.recovery_datastore_names_by_site.setdefault(
                site_name,
                [],
            ).append(datastore_name)

    config.recovery_folder_names = [
        folder["Folder Name"]
        for folder in config.recovery_folders
        if folder.get("Folder Name")
    ]
    config.recovery_folder_names_by_site = {}
    for folder in config.recovery_folders:
        site_name = folder.get("Recovery ZVM Site Name")
        folder_name = folder.get("Folder Name")

        if site_name and folder_name:
            config.recovery_folder_names_by_site.setdefault(
                site_name,
                [],
            ).append(folder_name)

    config.recovery_network_names = [
        network["Network Name"]
        for network in config.recovery_networks
        if network.get("Network Name")
    ]
    config.recovery_network_names_by_site = {}
    for network in config.recovery_networks:
        site_name = network.get("Recovery ZVM Site Name")
        network_name = network.get("Network Name")

        if site_name and network_name:
            config.recovery_network_names_by_site.setdefault(
                site_name,
                [],
            ).append(network_name)
