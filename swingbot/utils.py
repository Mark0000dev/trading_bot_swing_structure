import os
from datetime import datetime
from pathlib import Path


def hourly_output_path(base_dir: Path, name: str, ext: str) -> Path:
    """base_dir/YYYY-MM-DD/HH-00/name.ext (adds a suffix if the file already exists)."""
    now = datetime.now()
    folder = Path(base_dir) / now.strftime("%Y-%m-%d") / now.strftime("%H-00")
    os.makedirs(folder, exist_ok=True)

    path = folder / f"{name}.{ext}"
    if path.exists():
        path = folder / f"{name}_{now.strftime('%M-%S-%f')}.{ext}"
    return path
