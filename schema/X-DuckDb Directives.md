Here's a comprehensive table of all x-duckdb directives we've defined:

| Directive | Function | Example Definition | Example SQL Output |
|-----------|----------|-------------------|-------------------|
| **x-duckdb-table** | Specifies the table name for this schema node | `"signatures": { "type": "array", "x-duckdb-table": "signatures" }` | `CREATE TABLE signatures (...)` |
| **x-duckdb-pk** | Defines the primary key column name | `"x-duckdb-pk": "uuid"` | `uuid VARCHAR PRIMARY KEY` |
| **x-duckdb-pk-type** | Specifies the data type for the primary key (default: VARCHAR) | `"x-duckdb-pk": "signature_id", "x-duckdb-pk-type": "INTEGER"` | `signature_id INTEGER PRIMARY KEY` |
| **x-duckdb-pk-seq** | Defines the SEQUENCE object to use for auto-incrementing the PK. Used when no natural PK exists | `"x-duckdb-pk-seq": "certificate_seq"` | `CREATE SEQUENCE certificate_seq; PRIMARY KEY DEFAULT NEXTVAL('certificate_seq')` |
| **x-duckdb-fk** | Defines the foreign key column name referencing parent table | `"x-duckdb-fk": "observation_uuid"` | `observation_uuid VARCHAR, FOREIGN KEY (observation_uuid) REFERENCES observations(uuid)` |
| **x-duckdb-type** | Specifies the data type for this column (default: type defined in schema) | `"x-duckdb-type": "BIGINT"` | `bytesize BIGINT` | 
| **x-duckdb-flatten** | Flattens nested object properties into parent table with prefix | `"elfIdent": { "type": "object", "x-duckdb-flatten": true, "properties": {"EI_CLASS": {...}} }` | `elfIdent_EI_CLASS INTEGER DEFAULT NULL` (in parent table) |
| **x-duckdb-array** | Stores array as native DuckDB array type | `"elfDependencies": { "type": "array", "x-duckdb-array": true, "items": {"type": "string"} }` | `elfDependencies VARCHAR[] DEFAULT NULL` |
| **x-duckdb-json** | Stores complex nested structures as JSON | `"binaries": { "type": "array", "x-duckdb-json": true }` | `binaries JSON DEFAULT NULL` |
| **x-duckdb-value-column** | For primitive arrays in separate tables, names the value column | `"hosts": { "type": "array", "x-duckdb-table": "observation_hosts", "x-duckdb-value-column": "host" }` | `CREATE TABLE observation_hosts (observation_uuid VARCHAR, host VARCHAR)` |
| **x-duckdb-discriminator** | Field used to determine polymorphic type (oneOf) | `"metadata": { "x-duckdb-discriminator": "filetype", "oneOf": [...] }` | Used to populate `filetype_type` column and view WHERE clauses |
| **x-duckdb-when** | List of discriminator values that trigger this variant | `{"$ref": "#/$defs/ELFMetadata", "x-duckdb-when": ["ELF"]}` | `WHERE filetype_type = 'ELF'` (in view definition) |
| **x-duckdb-polymorphic-strategy** | Strategy for handling oneOf: "separate-tables" or "single-table" | `"x-duckdb-polymorphic-strategy": "single-table"` | **separate-tables**: Multiple tables (pe_metadata, elf_metadata)<br>**single-table**: One wide table + views |

## Polymorphic Strategy Comparison

### separate-tables (default)
```json
"metadata": {
  "x-duckdb-discriminator": "filetype",
  "x-duckdb-polymorphic-strategy": "separate-tables",
  "oneOf": [
    {"$ref": "#/$defs/PEMetadata", "x-duckdb-table": "pe_metadata", "x-duckdb-pk": "observation_uuid"}
  ]
}
```

```sql
CREATE TABLE pe_metadata (
  observation_uuid VARCHAR PRIMARY KEY,
  peMachine VARCHAR,
  peIsExe BOOLEAN DEFAULT NULL,
  FOREIGN KEY (observation_uuid) REFERENCES observations(uuid)
);
```

### single-table
```json
"metadata": {
  "x-duckdb-discriminator": "filetype",
  "x-duckdb-polymorphic-strategy": "single-table",
  "x-duckdb-table": "file_metadata",
  "oneOf": [
    {"$ref": "#/$defs/PEMetadata", "x-duckdb-table": "pe_metadata", "x-duckdb-when": ["PE"]}
  ]
}
```

```sql
CREATE TABLE file_metadata (
  observation_uuid VARCHAR PRIMARY KEY,
  filetype_type VARCHAR,
  peMachine VARCHAR DEFAULT NULL,
  peIsExe BOOLEAN DEFAULT NULL,
  elfDependencies VARCHAR[] DEFAULT NULL,
  -- all columns from all variants
  FOREIGN KEY (observation_uuid) REFERENCES observations(uuid)
);

CREATE VIEW pe_metadata AS
SELECT observation_uuid, peMachine, peIsExe, ...
FROM file_metadata
WHERE filetype_type = 'PE';
```