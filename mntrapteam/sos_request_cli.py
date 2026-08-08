from .sos_request_capture import capture_highgun_request


def main() -> int:
    capture_highgun_request()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
