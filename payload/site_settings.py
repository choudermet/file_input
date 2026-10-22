import json
from pathlib import Path
from payload.json_output import make_json_safe
from datetime import datetime

RUN_TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

def build_site_settings_file(excel_file: str | Path) -> Path:
    return Path("outputs") / (
        f"{Path(excel_file).stem}_site_settings_{RUN_TIMESTAMP}.json"
    )

def write_site_settings_json(
    site_settings: dict[str, list[dict]],
    excel_file: str | Path,
    output_file: str | Path | None = None,
) -> Path:
    output_path = (
        Path(output_file)
        if output_file
        else build_site_settings_file(excel_file)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(make_json_safe(site_settings), indent=2),
        encoding="utf-8",
    )

    return output_path
