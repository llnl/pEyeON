import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import streamlit as st
import yaml
import fnmatch

class DLTSchema:
    """Helper class to work with DLT schema as a tree structure"""
    
    def __init__(self, schema_path: str):
        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()
        
    def _load_schema(self) -> Dict[str, Any]:
        """Load schema from JSON or YAML file"""
        with open(self.schema_path, 'r') as f:
            if self.schema_path.suffix == '.json':
                return json.load(f)
            elif self.schema_path.suffix in ['.yaml', '.yml']:
                import yaml
                return yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported file type: {self.schema_path.suffix}")
    
    def get_tables(self) -> Dict[str, Dict]:
        """Get all tables in the schema"""
        return self.schema.get('tables', {})
    
    def get_parent_table(self, table_name: str) -> Optional[str]:
        """Get the immediate parent table name, or None if no parent"""
        table_def = self.get_table(table_name)
        return table_def.get('parent', None)

    
    def get_table(self, table_name: str) -> Dict[str, Any]:
        """Get a specific table definition"""
        return self.schema['tables'].get(table_name, {})
    
    def get_columns(self, table_name: str) -> Dict[str, Dict]:
        """Get columns for a specific table"""
        return self.get_table(table_name).get('columns', {})
    
    def list_tables(self) -> List[str]:
        """List all table names"""
        return list(self.schema['tables'].keys())
    
    def get_parent_child_relationships(self) -> Dict[str, List[str]]:
        """Map parent tables to their child tables"""
        relationships = {}
        for table_name, table_def in self.get_tables().items():
            if 'parent' in table_def:
                parent = table_def['parent']
                if parent not in relationships:
                    relationships[parent] = []
                relationships[parent].append(table_name)
        return relationships
    
    def print_schema_tree(self, table_name: str = None, indent: int = 0):
        """Print schema as a tree structure"""
        tree = []
        if table_name is None:
            # Start with root tables (no parent)
            root_tables = [t for t, d in self.get_tables().items() 
                          if 'parent' not in d]
            for root in sorted(root_tables):
                self.print_schema_tree(root)
        else:
            tree.append("  " * indent + f"├── {table_name}")
            table_def = self.get_table(table_name)
            
            # Print columns
            for col_name in sorted(table_def.get('columns', {}).keys()):
                col_def = table_def['columns'][col_name]
                col_type = col_def.get('data_type', 'unknown')
                print("  " * (indent + 1) + f"│   {col_name} ({col_type})")
            
            # Print child tables
            children = self.get_parent_child_relationships().get(table_name, [])
            for child in sorted(children):
                self.print_schema_tree(child, indent + 5)
        
        st.markdown('\n'.join(tree))

def load_overlay(path="eyeon_schema_overlay.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)

def get_enriched_schema(pipeline, overlay_path="eyeon_schema_overlay.yaml"):
    """Merge DLT's live schema with your overlay for tooling/docs use."""
    overlay = load_overlay(overlay_path)
    schema = pipeline.default_schema
    result = {}

    for table_name, table_def in schema.tables.items():
        entry = {
            "columns": {k: v for k, v in table_def.get("columns", {}).items()
                        if not k.startswith("_dlt")},
            "description": None,
            "parent_table": None,
            "join": None,
        }

        # Apply descriptions
        td = overlay.get("table_descriptions", {})
        if table_name in td:
            entry["description"] = td[table_name].get("description")

        # Apply relationship patterns
        for rel in overlay.get("relationships", []):
            if fnmatch.fnmatch(table_name, rel["child_table_pattern"]):
                entry["parent_table"] = rel["parent_table"]
                entry["join"] = rel["join"]
                break

        result[table_name] = entry

    return result