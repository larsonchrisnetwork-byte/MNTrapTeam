from pathlib import Path
import re

VERSION = "3.11.1"
TARGET = Path("mntrapteam/scoreboard_central_zone_capture_cli.py")
OLD_IMPORT = 'from .connectors import SessionStore, _load_playwright\n'
NEW_IMPORT = 'from .connectors import _load_playwright\n'
OLD_PROFILE = '    store = SessionStore(DATA)\n    profile = store.profile_dir("shootscoreboard")\n'
NEW_PROFILE = '    profile = DATA / "browser_profiles" / "shootscoreboard"\n    profile.mkdir(parents=True, exist_ok=True)\n'

def main():
    if not TARGET.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    text = TARGET.read_text(encoding="utf-8")

    if OLD_IMPORT in text:
        text = text.replace(OLD_IMPORT, NEW_IMPORT, 1)

    if OLD_PROFILE in text:
        text = text.replace(OLD_PROFILE, NEW_PROFILE, 1)
    elif NEW_PROFILE not in text:
        raise RuntimeError(
            "Could not patch ShootScoreBoard profile initialization."
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
        for i, line in enumerate(lines):
            if line.strip().startswith("__version__"):
                lines[i] = f'__version__ = "{VERSION}"'
                break
        else:
            lines.append(f'__version__ = "{VERSION}"')
        init.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        "MNTrapTeam 3.11.1 applied: ShootScoreBoard now uses its own "
        "browser profile folder instead of the connector provider registry."
    )

if __name__ == "__main__":
    main()
