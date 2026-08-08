from pathlib import Path
import re

VERSION = "3.6.8"
TARGET = Path("mntrapteam/myata_bulk_dom_cli.py")
HELPER = 'def _ranked_search_fields(page):\n    """Return Search/Buddies inputs with the ATA-number field first."""\n    candidates = page.locator("ata-shooter-information-center input")\n\n    if candidates.count() == 0:\n        candidates = page.locator("input")\n\n    ranked = []\n\n    for index in range(candidates.count()):\n        field = candidates.nth(index)\n\n        try:\n            if not field.is_visible() or field.is_disabled():\n                continue\n        except Exception:\n            continue\n\n        try:\n            metadata = field.evaluate(\n                """(el) => {\n                    const parts = [\n                        el.getAttribute(\'name\') || \'\',\n                        el.getAttribute(\'id\') || \'\',\n                        el.getAttribute(\'placeholder\') || \'\',\n                        el.getAttribute(\'aria-label\') || \'\',\n                        el.getAttribute(\'title\') || \'\'\n                    ];\n\n                    if (el.labels) {\n                        for (const label of el.labels) {\n                            parts.push(label.innerText || \'\');\n                        }\n                    }\n\n                    let node = el.parentElement;\n                    for (let i = 0; i < 3 && node; i++, node = node.parentElement) {\n                        parts.push(node.innerText || \'\');\n                    }\n\n                    return parts.join(\' \').replace(/\\\\s+/g, \' \').trim();\n                }"""\n            )\n        except Exception:\n            metadata = ""\n\n        upper = str(metadata or "").upper()\n\n        score = 0\n\n        if "ATA NUMBER" in upper:\n            score += 100\n        elif "ATA #" in upper or "ATA#" in upper:\n            score += 95\n        elif "ATA" in upper:\n            score += 80\n\n        if "LAST NAME" in upper:\n            score -= 30\n\n        if "FIRST NAME" in upper:\n            score -= 30\n\n        ranked.append((score, index, field, metadata))\n\n    ranked.sort(\n        key=lambda item: (\n            -item[0],\n            item[1],\n        )\n    )\n\n    return ranked\n'
OLD = '    candidates = page.locator("ata-shooter-information-center input")\n\n    if candidates.count() == 0:\n        candidates = page.locator("input")\n\n    for index in range(candidates.count()):\n        field = candidates.nth(index)\n\n        try:\n            if not field.is_visible() or field.is_disabled():\n                continue\n        except Exception:\n            continue\n\n        try:\n'
NEW = '    ranked_fields = _ranked_search_fields(page)\n\n    for _score, _index, field, _metadata in ranked_fields:\n        try:\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    marker = "def _find_result_button(page, name):\n"

    if "_ranked_search_fields(page)" not in text:
        if marker not in text:
            raise RuntimeError("Could not find Search/Buddies helper insertion point.")
        text = text.replace(marker, HELPER + "\n\n" + marker, 1)

    if OLD in text:
        text = text.replace(OLD, NEW, 1)
    elif NEW not in text:
        raise RuntimeError("Could not find Search/Buddies candidate loop.")

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
        "MNTrapTeam 3.6.8 applied: Search/Buddies now prioritizes ATA Number."
    )

if __name__ == "__main__":
    main()
