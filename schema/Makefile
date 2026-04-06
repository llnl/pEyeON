PYTHON = python3
DCG = datamodel-codegen
SCHEMA = observation.schema.json
MODELS = eyeon_models.py
DDL = eyeon_ddl.sql

.PHONY: all clean models ddl regen

all: models ddl

models: $(SCHEMA)
	$(PYTHON) -m pip show datamodel-code-generator >/dev/null || $(PYTHON) -m pip install datamodel-code-generator
	$(DCG) \
		--input $(SCHEMA) \
		--input-file-type jsonschema \
		--target-python-version 3.13 \
		--output $(MODELS) \
		--class-name ObservationModel \
		--use-standard-collections \
		--output-model-type pydantic_v2.BaseModel \
		--use-default

ddl: $(SCHEMA)
	$(PYTHON) gen_ddl.py $(SCHEMA) > $(DDL)

regen: clean all

clean:
	rm -f $(MODELS) $(DDL)