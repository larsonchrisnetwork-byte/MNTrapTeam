from .myata_broad_capture import capture_all_myata_json


def main() -> int:
    capture_all_myata_json()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
