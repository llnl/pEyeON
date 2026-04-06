# Simple loader for raw surfactant output. Used for initial testing and debugging.
#
# After running, you'll have a duckdb database (surfactant.duckdb). You can inspect this with duckdb.
# DLT also has a "dashboard" as another way to inspect data and the pipeline processing: `dlt dashboard`
#
# Note: Data files are expected to be python literals from `repr`
# Example: [{"key": "value"}, {"flag": True, "items": [1, 2]}]

import dlt
from dlt.sources.filesystem import filesystem
import ast
from pathlib import Path
from urllib.parse import urlparse, unquote
import logging
import argparse

# Read files and parse
@dlt.resource
def parse_text_files(path):
    for file_item in filesystem(path, file_glob="*.txt"):
        file_url = file_item['file_url']
        file_path = unquote(urlparse(file_url).path)
        
        # Read the file
        p = Path(file_path)
        content = p.read_text()
        parsed = ast.literal_eval(content)
        for record in parsed:
            record = sanitize_record(record)
            record['source_file'] = file_item['file_name']
            yield record

def sanitize_record(obj):
    """Recursively remove or sanitize binary data"""
    if isinstance(obj, dict):
        return {k: sanitize_record(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_record(item) for item in obj]
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif isinstance(obj, str):
        # Remove null bytes and other problematic chars
        return obj.replace('\x00', '').replace('\ufffd', '')
    else:
        return obj

def main(argv=None) -> None:
    logging.basicConfig(
    level=logging.INFO,                  # Change to DEBUG if you need more verbosity
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    )

    parser = argparse.ArgumentParser(
        prog="load_raw_surfactant.py", description="Load raw surfactant text files into tables."
    )
    parser.add_argument('--source', required=True, help='Source path of JSON files')

    args = parser.parse_args()

    # Create a pipeline
    pipeline = dlt.pipeline(
        pipeline_name="surfactant",
        destination="duckdb",
        dataset_name="surf"
    )

    load_info = pipeline.run(parse_text_files(args.source))

    # Access schema changes from the current run
    # Note: this uses the metadata that is written to a file by DLT. 
    # A more comprehensive approach is implemented in `schema_blame.py`
    for package in load_info.load_packages:
        for table_name, table in package.schema_update.items():
            for column_name, column in table["columns"].items():
                print(f"Table: {table_name}, Column: {column_name}, Type: {column['data_type']}")

if __name__ == "__main__":
    main()

