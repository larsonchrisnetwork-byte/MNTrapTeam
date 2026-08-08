from pathlib import Path
import re

VERSION="3.3.2"
DASH=Path("mntrapteam/live_dashboard.py")
GUI=Path("mntrapteam/gui.py")

def main():
    if not DASH.exists() or not GUI.exists():
        raise SystemExit("Run from H:\\MNTrapTeam\\MNTrapTeam")

    d=DASH.read_text(encoding="utf-8")
    imp="from .live_display import actionable_missing_requirements, rank_by_live_hoa"
    if imp not in d:
        anchor="from .haa_gate import haa_status"
        if anchor not in d: raise RuntimeError("Could not find dashboard import anchor")
        d=d.replace(anchor, anchor+"\n"+imp, 1)

    start=d.find("    rows.sort(")
    end=d.find("    summary = {", start)
    if start==-1 or end==-1:
        raise RuntimeError("Could not find the old Live Team ranking block")

    replacement=(
        "    team_size = int(team_service.rules.rules[\"teams\"][team][\"size\"])\n\n"
        "    ranked = rank_by_live_hoa(rows, team_size)\n"
        "    rows = ranked[\"rows\"]\n"
        "    live_cut = ranked[\"projected_cut_hoa\"]\n"
        "    eligible_cut = ranked[\"eligible_cut_hoa\"]\n\n"
        "    qualified = [row for row in rows if row[\"haa_qualified\"]]\n"
        "    eligible_qualified = [row for row in qualified if bool(row.get(\"eligible\"))]\n"
        "    selected = eligible_qualified[:team_size]\n\n"
        "    for row in rows:\n"
        "        row[\"live_team\"] = row in selected\n\n"
    )
    d=d[:start]+replacement+d[end:]

    if '"eligible_cut_hoa": eligible_cut,' not in d:
        d=d.replace(
            '"live_cut_hoa": live_cut,\n',
            '"live_cut_hoa": live_cut,\n            "eligible_cut_hoa": eligible_cut,\n',
            1,
        )

    marker='        reasons = ranking.get("eligibility_reasons") or []\n'
    pos=d.find(marker)
    if pos==-1: raise RuntimeError("Could not find eligibility reasons block")
    rowpos=d.find("\n\n        row = dict(ranking)", pos)
    if rowpos==-1: raise RuntimeError("Could not find end of eligibility reasons block")
    newreasons=(
        '        reasons = ranking.get("eligibility_reasons") or []\n'
        '        eligibility = team_service.rules.check(ranking, team)\n'
        '        progress = eligibility.progress\n'
        '        reasons_text = actionable_missing_requirements(progress, reasons)\n'
    )
    d=d[:pos]+newreasons+d[rowpos:]
    compile(d, str(DASH), "exec")
    DASH.write_text(d, encoding="utf-8")

    g=GUI.read_text(encoding="utf-8")
    g=g.replace('("live_pool_rank","Pool Rank"),', '("live_pool_rank","Projected Rank"),', 1)
    g=g.replace('("live_cut_hoa","Cut"),', '("live_cut_hoa","Projected Cut"),', 1)
    g=g.replace('("live_gap_to_cut","Gap"),', '("live_gap_to_cut","Gap to Projected Cut"),', 1)
    g=g.replace('("eligibility_reasons_text","Missing Requirements"),', '("eligibility_reasons_text","What Is Needed"),', 1)
    g=re.sub(r"self\\.setWindowTitle\\(\'MNTrapTeam [^\']+\'\\)", f"self.setWindowTitle(\'MNTrapTeam {VERSION}\')", g, count=1)
    compile(g, str(GUI), "exec")
    GUI.write_text(g, encoding="utf-8")

    Path("VERSION").write_text(VERSION+"\n", encoding="utf-8")
    init=Path("mntrapteam/__init__.py")
    value=init.read_text(encoding="utf-8") if init.exists() else ""
    if "__version__" in value:
        value=re.sub(r'__version__\\s*=\\s*["\\\'][^"\\\']+["\\\']', f'__version__ = "{VERSION}"', value, count=1)
    else:
        value=value.rstrip()+f'\n\n__version__ = "{VERSION}"\n'
    init.write_text(value, encoding="utf-8")
    print("MNTrapTeam 3.3.2 applied: HOA-only ordering and actionable requirements.")

if __name__=="__main__":
    main()