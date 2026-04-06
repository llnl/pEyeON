"""
schema_ext.py

Decorator-pattern schema enrichment for DLT pipelines.

Usage:
    from schema_ext import DltSchema, OverlayDecorator, RelationshipDecorator

    schema = RelationshipDecorator(
                OverlayDecorator(
                    DltSchema(pipeline),
                    overlay_path="schema_ext_overlay.yaml"
                )
             )

    table = schema.get_table("metadata_java_file__javaClasses")
    all_tables = schema.get_all_tables()
    children = table.get_children()   # [EnrichedTable, ...]

    # Arbitrary YAML attributes are accessible via .extra or directly:
    #   table.search_field   (raises AttributeError if absent)
    #   table.extra.get("search_field")  (safe)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
import fnmatch
import yaml


# ---------------------------------------------------------------------------
# Known overlay keys consumed explicitly by OverlayDecorator.
# Any key NOT in this set is forwarded to EnrichedTable.extra.
# ---------------------------------------------------------------------------

_KNOWN_OVERLAY_KEYS = {"description", "columns", "nested"}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ColumnDef:
    name: str
    data_type: Optional[str] = None
    nullable: Optional[bool] = None
    description: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def __getattr__(self, item: str):
        extra = self.__dict__.get("extra")
        if extra is not None and item in extra:
            return extra[item]
        raise AttributeError(f"{type(self).__name__!r} has no attribute {item!r}")

    @classmethod
    def from_dlt(cls, name: str, dlt_col: dict) -> "ColumnDef":
        return cls(
            name=name,
            data_type=dlt_col.get("data_type"),
            nullable=dlt_col.get("nullable"),
        )

@dataclass
class JoinDef:
    child_col: str
    parent_col: str
    note: Optional[str] = None


@dataclass
class EnrichedTable:
    name: str
    # Hierarchy
    depth: int = 0
    hierarchy_path: list[str] = field(default_factory=list)
    parent_table: Optional[str] = None     # immediate DLT parent (__ separated)
    root_table: Optional[str] = None       # top-level ancestor
    orphan_parent: Optional[str] = None    # # Workaround: manually parent metadata_* tables to raw_obs until DLT supports it natively.
    # Join
    join: Optional[JoinDef] = None
    # Enrichment
    description: Optional[str] = None
    columns: dict[str, ColumnDef] = field(default_factory=dict)
    # Catch-all for arbitrary YAML attributes (e.g. search_field, display_name, …)
    extra: dict = field(default_factory=dict)
    # Raw DLT table def for anything we haven't modelled
    _dlt_raw: dict = field(default_factory=dict, repr=False)
    # Back-reference injected by RelationshipDecorator; not part of the public model
    _schema_ref: Optional[Callable[[], dict[str, "EnrichedTable"]]] = field(
        default=None, repr=False, compare=False
    )

    def __getattr__(self, item: str):
        """
        Transparent proxy into `extra` so callers can write table.search_field
        instead of table.extra["search_field"].  Only reached when normal
        attribute lookup fails (i.e. item is not a real dataclass field).
        """
        # Guard against infinite recursion during unpickling / copy
        extra = self.__dict__.get("extra")
        if extra is not None and item in extra:
            return extra[item]
        else:
            return None
        #raise AttributeError(f"{type(self).__name__!r} has no attribute {item!r}")

    def get_children(self) -> list["EnrichedTable"]:
        """
        Return all tables whose immediate parent (DLT or orphan) is this table.
        Requires that this instance was produced by RelationshipDecorator.
        """
        if self._schema_ref is None:
            return []
        return [t for t in self._schema_ref().values() if t.get_parent() == self.name]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "depth": self.depth,
            "hierarchy_path": self.hierarchy_path,
            "parent_table": self.parent_table,
            "root_table": self.root_table,
            "orphan_parent": self.orphan_parent,
            "join": vars(self.join) if self.join else None,
            "description": self.description,
            "columns": {k: vars(v) for k, v in self.columns.items()},
            "extra": self.extra,
        }

    def get_parent(self):
        return self.orphan_parent if self.orphan_parent else self.parent_table


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class SchemaProvider(ABC):

    @abstractmethod
    def get_table(self, name: str) -> Optional[EnrichedTable]:
        ...

    @abstractmethod
    def get_all_tables(self) -> dict[str, EnrichedTable]:
        ...


# ---------------------------------------------------------------------------
# Layer 1: DLT schema — raw data, no enrichment
# ---------------------------------------------------------------------------

class DltSchema(SchemaProvider):
    """
    Wraps a live DLT pipeline schema. Produces minimally-populated
    EnrichedTable objects from whatever DLT knows.
    """

    def __init__(self, pipeline):
        self._pipeline = pipeline

    def _dlt_tables(self) -> dict:
        return self._pipeline.default_schema.tables

    def _build(self, name: str, dlt_table: dict) -> EnrichedTable:
        cols = {
            k: ColumnDef.from_dlt(k, v)
            for k, v in dlt_table.get("columns", {}).items()
            if not k.startswith("_dlt")
        }
        return EnrichedTable(name=name, columns=cols, _dlt_raw=dlt_table)

    def get_table(self, name: str) -> Optional[EnrichedTable]:
        tables = self._dlt_tables()
        if name not in tables:
            return None
        return self._build(name, tables[name])

    def get_all_tables(self) -> dict[str, EnrichedTable]:
        return {name: self._build(name, t) for name, t in self._dlt_tables().items()}


# ---------------------------------------------------------------------------
# Layer 2: Overlay decorator — human-authored descriptions and directives from YAML
# ---------------------------------------------------------------------------

class OverlayDecorator(SchemaProvider):
    """
    Merges a YAML overlay into EnrichedTable objects.

    Known keys (description, columns, nested) are handled explicitly.
    Any other key is forwarded verbatim into EnrichedTable.extra, making
    new YAML attributes instantly available in Python without code changes:

        # schema_ext_overlay.yaml
        table_descriptions:
          metadata_java_file:
            description: "..."
            search_field: "classname"   # ← new, no Python changes needed

        # Python
        table.search_field   # → "classname"
        table.extra.get("search_field")  # → "classname" (safe access)

    YAML shape:
        table_descriptions:
          raw_obs:
            description: "..."
            columns:
              uuid: "Primary key"
          metadata_java_file:
            description: "..."
            search_field: "classname"
            nested:
              javaClasses:
                description: "..."
                columns:
                  classname: "..."
                nested:
                  methods:
                    description: "..."
    """

    def __init__(self, inner: SchemaProvider, overlay_path: str = "schema_ext_overlay.yaml"):
        self._inner = inner
        self._overlay = self._load(overlay_path)

    @staticmethod
    def _load(path: str) -> dict:
        p = Path(path)
        if not p.exists():
            return {}
        with open(p) as f:
            return yaml.safe_load(f) or {}

    def _find_overlay_node(self, hierarchy_path: list[str]) -> Optional[dict]:
        """
        Walk the nested overlay tree using the hierarchy path.
        ["metadata_java_file", "javaClasses", "methods"]
        → table_descriptions["metadata_java_file"]["nested"]["javaClasses"]["nested"]["methods"]
        """
        td = self._overlay.get("table_descriptions", {})
        node = td.get(hierarchy_path[0])
        for part in hierarchy_path[1:]:
            if node and "nested" in node:
                node = node["nested"].get(part)
            else:
                return None
        return node

    def _enrich(self, table: EnrichedTable) -> EnrichedTable:
        path = table.hierarchy_path if table.hierarchy_path else [table.name]
        node = self._find_overlay_node(path)
        if not node:
            return table

        table.description = node.get("description", table.description)

        for col_name, val in node.get("columns", {}).items():
            if isinstance(val, str):
                desc, col_extra = val, {}
            else:
                desc, col_extra = val.get("description"), {k: v for k, v in val.items() if k != "description"}

            if col_name in table.columns:
                table.columns[col_name].description = desc
                table.columns[col_name].extra.update(col_extra)
            else:
                table.columns[col_name] = ColumnDef(name=col_name, description=desc, extra=col_extra)

        # Forward any unrecognised keys into extra
        table.extra.update({k: v for k, v in node.items() if k not in _KNOWN_OVERLAY_KEYS})

        return table

    def get_table(self, name: str) -> Optional[EnrichedTable]:
        table = self._inner.get_table(name)
        return self._enrich(table) if table else None

    def get_all_tables(self) -> dict[str, EnrichedTable]:
        return {name: self._enrich(t) for name, t in self._inner.get_all_tables().items()}


# ---------------------------------------------------------------------------
# Layer 3: Relationship decorator — hierarchy + join resolution
# ---------------------------------------------------------------------------

class RelationshipDecorator(SchemaProvider):
    """
    Derives parent/child relationships and join keys from DLT's __ naming
    convention. Requires no YAML — all hierarchy is algorithmic.

    Nested table joins use DLT internal keys (_dlt_parent_id → _dlt_id).
    Root metadata table joins use uuid → uuid against raw_obs.

    Also injects a _schema_ref callable into each EnrichedTable so that
    table.get_children() can resolve its direct children on demand.
    """

    # Tables that are DLT system tables, not part of any hierarchy
    SYSTEM_TABLES = {"_dlt_loads", "_dlt_pipeline_state", "_dlt_version"}

    def __init__(self, inner: SchemaProvider,
                 orphan_root_pattern: str = "metadata_*",
                 orphan_parent: str = "raw_obs"):
        self._inner = inner
        self._orphan_root_pattern = orphan_root_pattern
        self._orphan_parent = orphan_parent

    @staticmethod
    def _parse_hierarchy(name: str) -> dict:
        parts = name.split("__")
        return {
            "depth":     len(parts) - 1,
            "path":      parts,
            "root":      parts[0],
            "parent":    "__".join(parts[:-1]) if len(parts) > 1 else None,
            "is_nested": len(parts) > 1,
        }

    def _enrich(self, table: EnrichedTable) -> EnrichedTable:
        if table.name in self.SYSTEM_TABLES:
            return table

        h = self._parse_hierarchy(table.name)
        table.depth          = h["depth"]
        table.hierarchy_path = h["path"]
        table.root_table     = h["root"]
        table.parent_table   = h["parent"]

        is_orphan_root = (
            not h["is_nested"]
            and fnmatch.fnmatch(table.name, self._orphan_root_pattern)
        )

        if is_orphan_root:
            table.orphan_parent = self._orphan_parent
            table.join = JoinDef(
                child_col="uuid",
                parent_col="uuid",
                note=f"orphan key join to {self._orphan_parent}"
            )
        elif h["is_nested"]:
            table.join = JoinDef(
                child_col="_dlt_parent_id",
                parent_col="_dlt_id",
                note="DLT internal keys; trace uuid up hierarchy for orphan joins"
            )

        # Inject back-reference so get_children() can resolve lazily.
        # We capture `self` rather than a snapshot so the lookup always
        # reflects the current schema state.
        table._schema_ref = self.get_all_tables
        return table

    def get_table(self, name: str) -> Optional[EnrichedTable]:
        table = self._inner.get_table(name)
        return self._enrich(table) if table else None

    def get_all_tables(self) -> dict[str, EnrichedTable]:
        return {name: self._enrich(t) for name, t in self._inner.get_all_tables().items()}


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def build_schema(pipeline,
                 overlay_path: str = "schema_ext_overlay.yaml") -> SchemaProvider:
    """
    Convenience factory that assembles the full decorator stack:
        DltSchema → OverlayDecorator → RelationshipDecorator
    """
    return RelationshipDecorator(
        OverlayDecorator(
            DltSchema(pipeline),
            overlay_path=overlay_path
        )
    )