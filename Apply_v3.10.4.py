from pathlib import Path
import re

VERSION = "3.10.4"
TARGET = Path("mntrapteam/zone_residence_south_cli.py")
OLD = 'def _page_with_ata_field(context):\n    for page in reversed(context.pages):\n        try:\n            loc = page.locator(\'input[placeholder="ATA Number"]\')\n            if loc.count() and loc.first.is_visible():\n                return page\n        except Exception:\n            continue\n    return None\n'
NEW = 'def _page_with_ata_field(context):\n    for page in reversed(context.pages):\n        try:\n            loc = page.locator(\'input[placeholder="ATA Number"]\')\n            if loc.count() and loc.first.is_visible():\n                return page\n        except Exception:\n            continue\n\n    for page in reversed(context.pages):\n        try:\n            if "shootata.com" not in (page.url or "").lower():\n                continue\n            try:\n                page.get_by_role("button", name="Search/Buddies").click(timeout=4000)\n                page.wait_for_timeout(700)\n            except Exception:\n                pass\n            loc = page.locator(\'input[placeholder="ATA Number"]\')\n            if loc.count():\n                return page\n        except Exception:\n            continue\n\n    candidate = None\n    for page in reversed(context.pages):\n        try:\n            if "shootata.com" in (page.url or "").lower():\n                candidate = page\n                break\n        except Exception:\n            continue\n\n    if candidate is None:\n        candidate = context.new_page()\n\n    try:\n        candidate.goto(MYATA_URL, wait_until="domcontentloaded", timeout=60000)\n        candidate.wait_for_timeout(700)\n        try:\n            candidate.get_by_role("button", name="Search/Buddies").click(timeout=5000)\n            candidate.wait_for_timeout(700)\n        except Exception:\n            pass\n        loc = candidate.locator(\'input[placeholder="ATA Number"]\')\n        if loc.count():\n            return candidate\n    except Exception:\n        pass\n\n    return None\n'
OLD_FAIL = '        page = _page_with_ata_field(context)\n        if page is None:\n            raise RuntimeError("No open MyATA page contains the ATA Number field")\n\n        print(f"Using MyATA page: {page.url}")\n'
NEW_FAIL = '        page = _page_with_ata_field(context)\n        if page is None:\n            print()\n            print("OPEN BROWSER PAGES CHECKED:")\n            for index, candidate_page in enumerate(context.pages):\n                try:\n                    print(f"  [{index}] {candidate_page.url}")\n                except Exception:\n                    print(f"  [{index}] <unavailable>")\n            raise RuntimeError(\n                "Could not open/find the MyATA Search/Buddies ATA Number field"\n            )\n\n        print(f"Using MyATA page: {page.url}")\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    if OLD in text:
        text = text.replace(OLD, NEW, 1)
    elif NEW not in text:
        raise RuntimeError("Could not find Southern page-selection function.")

    if OLD_FAIL in text:
        text = text.replace(OLD_FAIL, NEW_FAIL, 1)

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")

    Path("VERSION").write_text(VERSION + "\n", encoding="utf-8")

    gui = Path("mntrapteam/gui.py")
    if gui.exists():
        g = gui.read_text(encoding="utf-8")
        g = re.sub(r"MNTrapTeam \d+\.\d+\.\d+", f"MNTrapTeam {VERSION}", g, count=1)
        gui.write_text(g, encoding="utf-8")

    init = Path("mntrapteam/__init__.py")
    if init.exists():
        lines = init.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[i] = f'__version__ = "{VERSION}"'
                break
        else:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("MNTrapTeam 3.10.4 applied: robust Southern MyATA page recovery added.")

if __name__ == "__main__":
    main()
