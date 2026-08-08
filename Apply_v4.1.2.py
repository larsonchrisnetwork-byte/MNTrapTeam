from pathlib import Path
import re

VERSION = "4.1.2"
TARGET = Path("mntrapteam/myata_bulk_dom_cli.py")

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    # Add csv import if missing.
    if "import csv\n" not in text:
        text = text.replace("import argparse\n", "import argparse\nimport csv\n", 1)

    # Add --ata-file argument after parser creation/season-ish args.
    marker = 'parser.add_argument("--season"'
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find argparse section in myata_bulk_dom_cli.py")

    # Find end of the season add_argument statement.
    end = text.find("\n", idx)
    insert_arg = (
        '\n    parser.add_argument(\n'
        '        "--ata-file",\n'
        '        help="CSV file containing ata_number and optional display_name columns",\n'
        '    )\n'
    )
    if '--ata-file' not in text:
        text = text[:end+1] + insert_arg + text[end+1:]

    # Inject helper for reading targeted ATA file.
    helper = r