import json
from pathlib import Path

folder = Path(r"data/connector_downloads/myata/20260806_183954")
items = json.loads((folder / "network_json.json").read_text(encoding="utf-8"))

for index, item in enumerate(items, 1):
    body = item.get("body")
    print(f"\n--- RESPONSE {index} ---")
    print("URL:", item.get("url"))

    if isinstance(body, dict):
        print("Top-level keys:", list(body.keys())[:50])
        for key, value in body.items():
            if isinstance(value, list):
                print(f"  {key}: list[{len(value)}]")
                if value and isinstance(value[0], dict):
                    print("    first-item keys:", list(value[0].keys())[:50])
            elif isinstance(value, dict):
                print(f"  {key}: object keys={list(value.keys())[:30]}")
            else:
                print(f"  {key}: {type(value).__name__}")

    elif isinstance(body, list):
        print("List length:", len(body))
        if body and isinstance(body[0], dict):
            print("First-item keys:", list(body[0].keys())[:50])
    else:
        print("Type:", type(body).__name__)
