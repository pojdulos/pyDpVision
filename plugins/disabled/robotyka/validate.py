import json, jsonschema, os

if __name__ == "__main__":
    schema_filename = "dhjoint_schema.json"
    try:
        schema = open(schema_filename).read()
    except FileNotFoundError:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            schema = open(os.path.join(script_dir, schema_filename)).read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File {schema_filename} not found in the current directory or script directory.")

    model_filename = "hand_model.json"
    try:
        model = open(model_filename).read()
    except FileNotFoundError:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            model = open(os.path.join(script_dir, model_filename)).read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File {model_filename} not found in the current directory or script directory.")

    try:
        jsonschema.validate(instance=json.loads(model), schema=json.loads(schema))
        print("✓ Walidacja przeszła pomyślnie!")
    except jsonschema.ValidationError as e:
        print(f"✗ Błąd walidacji: {e.message}")
        print(f"Ścieżka: {' -> '.join(str(p) for p in e.path)}")
    except jsonschema.SchemaError as e:
        print(f"✗ Błąd w schemacie: {e.message}")
