"""Export FastAPI OpenAPI schema to api/openapi.yaml and api/openapi.json."""

import json
import os

import yaml

from app.main import app


def main() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    api_dir = os.path.join(repo_root, "api")
    os.makedirs(api_dir, exist_ok=True)

    schema = app.openapi()
    schema["servers"] = [
        {"url": "http://localhost:8000", "description": "Local Development Server"},
        {"url": "https://api.maancamera.com", "description": "Production Server"},
    ]

    yaml_path = os.path.join(api_dir, "openapi.yaml")
    with open(yaml_path, "w", encoding="utf-8", newline="\n") as yf:
        yaml.safe_dump(schema, yf, sort_keys=False, allow_unicode=True)

    json_path = os.path.join(api_dir, "openapi.json")
    with open(json_path, "w", encoding="utf-8", newline="\n") as jf:
        json.dump(schema, jf, indent=2)
        jf.write("\n")

    print(f"Exported {len(schema.get('paths', {}))} OpenAPI paths to {yaml_path} and {json_path}")


if __name__ == "__main__":
    main()
