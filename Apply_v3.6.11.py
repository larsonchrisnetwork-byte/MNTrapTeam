from pathlib import Path
import re

VERSION = "3.6.11"
TARGET = Path("mntrapteam/myata_bulk_dom_cli.py")
OLD = 'def _find_result_button(page, name):\n    parts = [part for part in re.split(r"\\s+", str(name).strip()) if part]\n    if not parts:\n        return None\n\n    first = parts[0].upper()\n    last = parts[-1].upper()\n\n    buttons = page.locator("button")\n    for index in range(buttons.count()):\n        button = buttons.nth(index)\n        try:\n            text = " ".join(button.inner_text(timeout=500).split()).upper()\n        except Exception:\n            continue\n\n        # MyATA result example:\n        # WEBER, AIDEN KENITH. - MONTICELLO, MN\n        if first in text and last in text:\n            return button\n\n    return None\n'
NEW = 'def _find_result_button(page, name):\n    parts = [part for part in re.split(r"\\s+", str(name).strip()) if part]\n    first = parts[0].upper() if parts else ""\n    last = parts[-1].upper() if parts else ""\n\n    buttons = page.locator("ata-shooter-information-center button")\n    if buttons.count() == 0:\n        buttons = page.locator("button")\n\n    shooter_results = []\n\n    for index in range(buttons.count()):\n        button = buttons.nth(index)\n        try:\n            text = " ".join(button.inner_text(timeout=500).split()).upper()\n        except Exception:\n            continue\n\n        if not text:\n            continue\n\n        # Exclude the fixed Shooter Information Center navigation controls.\n        if text in {\n            "MY SCORES",\n            "SEARCH/BUDDIES",\n            "QUICK LIST",\n            "ALL AMERICAN",\n        }:\n            continue\n\n        # Search/Buddies shooter results are rendered like:\n        # WEBER, AIDEN KENITH. - MONTICELLO, MN\n        # Require the result-like comma + location separator pattern so an\n        # unrelated page button is not mistaken for a shooter.\n        if "," in text and " - " in text:\n            shooter_results.append((button, text))\n\n    # Exact ATA-number searches normally return one shooter. Trust that unique\n    # result even if our database uses a nickname (Eli) and ATA shows the\n    # formal first name (Elias).\n    if len(shooter_results) == 1:\n        return shooter_results[0][0]\n\n    # If more than one result is present, fall back to name matching.\n    for button, text in shooter_results:\n        if first and last and first in text and last in text:\n            return button\n\n    # Last-name-only fallback is safe only when it identifies a single result.\n    if last:\n        last_matches = [\n            button\n            for button, text in shooter_results\n            if last in text\n        ]\n        if len(last_matches) == 1:\n            return last_matches[0]\n\n    return None\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    if OLD in text:
        text = text.replace(OLD, NEW, 1)
    elif NEW not in text:
        raise RuntimeError("Could not find v3.6.8 result-button matcher.")

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    gui = Path("mntrapteam/gui.py")
    if gui.exists():
        g = gui.read_text(encoding="utf-8")
        g = re.sub(
            r"MNTrapTeam \d+\.\d+\.\d+",
            f"MNTrapTeam {VERSION}",
            g,
            count=1,
        )
        gui.write_text(g, encoding="utf-8")

    init = Path("mntrapteam/__init__.py")
    if init.exists():
        lines = init.read_text(encoding="utf-8").splitlines()
        found = False
        for index, line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[index] = f'__version__ = "{VERSION}"'
                found = True
                break
        if not found:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        "MNTrapTeam 3.6.11 applied: exact ATA searches accept a unique shooter "
        "result even when first-name aliases differ."
    )

if __name__ == "__main__":
    main()
