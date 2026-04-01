from pathlib import Path
from typing import Union

from dynaconf import Dynaconf


_DLT_DIR = Path(__file__).resolve().parents[1]
_SETTINGS_FILE = _DLT_DIR / "EyeOnData.toml"

settings = Dynaconf(
    envvar_prefix="EyeOnData_",
    settings_files=[str(_SETTINGS_FILE)],
)


def resolve_dlt_path(path: Union[str, Path]) -> Path:
    """Resolve a path relative to `schema/dlt/` unless already absolute."""
    p = Path(path).expanduser()
    return p if p.is_absolute() else (_DLT_DIR / p).resolve()


def duckdb_path() -> Path:
    """Absolute path to the configured DuckDB database file."""
    db_dir = resolve_dlt_path(settings.db.db_path)
    return (db_dir / settings.db.db_file).resolve()
