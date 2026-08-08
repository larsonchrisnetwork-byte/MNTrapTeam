from pathlib import Path
import re

VERSION = "3.6.2"
TARGET = Path("mntrapteam/myata_bulk_dom_cli.py")
OLD_FUNC = 'def _wait_for_yearly_summary(page, timeout_ms=15000):\n    try:\n        page.wait_for_function(\n            """() => Array.from(document.querySelectorAll(\'table\'))\n                .some(t => t.innerText.includes(\'Shooter Yearly Summary\'))""",\n            timeout=timeout_ms,\n        )\n        return True\n    except Exception:\n        return False\n'
NEW_FUNC = 'def _wait_for_yearly_summary(page, timeout_ms=15000):\n    """Wait for MyATA yearly summary through the web component shadow DOM."""\n    try:\n        locator = page.get_by_text("Shooter Yearly Summary", exact=True)\n        locator.first.wait_for(state="visible", timeout=timeout_ms)\n        return True\n    except Exception:\n        pass\n\n    try:\n        import time\n        deadline = time.monotonic() + (timeout_ms / 1000.0)\n        while time.monotonic() < deadline:\n            tables = page.locator("table")\n            for index in range(tables.count()):\n                table = tables.nth(index)\n                try:\n                    if "Shooter Yearly Summary" in table.inner_text(timeout=300):\n                        return True\n                except Exception:\n                    pass\n            page.wait_for_timeout(200)\n    except Exception:\n        pass\n\n    return False\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    if OLD_FUNC in text:
        text = text.replace(OLD_FUNC, NEW_FUNC, 1)
    elif "Wait for MyATA yearly summary through the web component shadow DOM." not in text:
        raise RuntimeError(
            "Could not find the v3.6.1 _wait_for_yearly_summary function."
        )

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
        for i, line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[i] = f'__version__ = "{VERSION}"'
                found = True
                break
        if not found:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        "MNTrapTeam 3.6.2 applied: "
        "MyATA shadow-DOM Yearly Summary detection fixed."
    )

if __name__ == "__main__":
    main()
