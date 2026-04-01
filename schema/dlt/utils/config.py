from pathlib import Path
import os
import tomllib
from typing import Any, Mapping, Union
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
    # Allow runtime override (used when invoking dbt and during first-time init).
    env_path = os.environ.get("EYEON_DUCKDB_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    db_dir = resolve_dlt_path(settings.db.db_path)
    return (db_dir / settings.db.db_file).resolve()


def eyeondata_toml_path() -> Path:
    return _SETTINGS_FILE


def _toml_escape_string(value: str) -> str:
    # Minimal TOML string escaping.
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _toml_format_value(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    return f'"{_toml_escape_string(str(value))}"'


def _deep_update(dst: dict[str, Any], src: Mapping[str, Any]) -> dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, Mapping) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = dict(v) if isinstance(v, Mapping) else v
    return dst


def update_eyeondata_toml(updates: Mapping[str, Any]) -> None:
    """Persist config updates to `EyeOnData.toml`.

    This keeps the file structure simple: only top-level tables (e.g. [db])
    with scalar values.
    """
    path = eyeondata_toml_path()
    existing: dict[str, Any] = {}
    if path.exists():
        existing = tomllib.loads(path.read_text(encoding="utf-8"))

    merged = _deep_update(existing, updates)

    # Write in a stable order for readability.
    section_order = ["datasets", "db", "defaults", "app"]
    sections = list(dict.fromkeys(section_order + sorted(merged.keys())))

    lines: list[str] = []
    for section in sections:
        value = merged.get(section)
        if not isinstance(value, dict):
            continue
        lines.append(f"[{section}]")
        for key in sorted(value.keys()):
            lines.append(f"{key} = {_toml_format_value(value[key])}")
        lines.append("")

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    os.replace(tmp_path, path)
