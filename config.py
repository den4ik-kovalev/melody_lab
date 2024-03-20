from pathlib import Path


app_dir = Path.home() / ".melody_lab"
temp_dir = app_dir / "temp"

app_dir.mkdir(exist_ok=True)
temp_dir.mkdir(exist_ok=True)
