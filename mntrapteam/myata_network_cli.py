from .myata_network_capture import capture_all_network


def main() -> int:
    capture_all_network()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
