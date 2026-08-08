import json
from pathlib import Path

path = Path(
    r"data\connector_downloads\sos\20260806_200406"
    r"\019_shootHighGunReport.json"
)

data = json.loads(path.read_text(encoding="utf-8"))
payload = data.get("payload", {})
report = payload.get("sortedReportData")

print("TOP PAYLOAD KEYS:")
print(list(payload.keys()))
print()

print("sortedReportData type:", type(report).__name__)

if isinstance(report, dict):
    print("sortedReportData keys:")
    print(list(report.keys())[:100])
    print()

    for key, value in list(report.items())[:20]:
        print(f"--- {key} ---")
        print("type:", type(value).__name__)

        if isinstance(value, list):
            print("count:", len(value))

            for i, item in enumerate(value[:3], 1):
                print(f"item {i} type:", type(item).__name__)

                if isinstance(item, dict):
                    print("keys:", list(item.keys())[:100])

                    safe = {}
                    for k, v in item.items():
                        if isinstance(v, (str, int, float, bool)) or v is None:
                            if any(
                                secret in k.lower()
                                for secret in (
                                    "email",
                                    "phone",
                                    "address",
                                    "token",
                                    "password",
                                )
                            ):
                                continue
                            safe[k] = v

                    print("sample:", safe)

        elif isinstance(value, dict):
            print("keys:", list(value.keys())[:100])

        print()

elif isinstance(report, list):
    print("count:", len(report))

    for i, item in enumerate(report[:5], 1):
        print()
        print(f"--- ITEM {i} ---")
        print("type:", type(item).__name__)

        if isinstance(item, dict):
            print("keys:", list(item.keys())[:100])

            safe = {}
            for k, v in item.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    if any(
                        secret in k.lower()
                        for secret in (
                            "email",
                            "phone",
                            "address",
                            "token",
                            "password",
                        )
                    ):
                        continue
                    safe[k] = v

            print("sample:", safe)

print()
print("EVENTS DATA:")
events = payload.get("eventsData")
print("type:", type(events).__name__)

if isinstance(events, list):
    print("count:", len(events))
    for i, item in enumerate(events[:20], 1):
        if isinstance(item, dict):
            print(i, list(item.keys())[:100])
            print(item)
elif isinstance(events, dict):
    print("keys:", list(events.keys())[:100])
    for key, value in list(events.items())[:20]:
        print(key, type(value).__name__)
        if isinstance(value, dict):
            print(value)
        elif isinstance(value, list):
            print("count:", len(value))
            if value and isinstance(value[0], dict):
                print("first keys:", list(value[0].keys())[:100])
                print("first item:", value[0])
