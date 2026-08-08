from pathlib import Path
import re

VERSION="3.3.0"
GUI=Path("mntrapteam/gui.py")
DASH=Path("mntrapteam/live_dashboard.py")

def main():
    if not GUI.exists() or not DASH.exists():
        raise SystemExit("Run from the MNTrapTeam repository root.")

    d=DASH.read_text(encoding="utf-8")
    imp="from .projected_ranking import apply_projected_ranking"
    if imp not in d:
        d=d.replace("from .haa_gate import haa_status", "from .haa_gate import haa_status\n"+imp, 1)

    start=d.find("    rows.sort(")
    end=d.find("    summary = {", start)
    if start == -1 or end == -1:
        raise RuntimeError("Could not find the v3.2 ranking block.")

    replacement = """    qualified = [row for row in rows if row["haa_qualified"]]
    eligible_qualified = [
        row for row in qualified if bool(row.get("eligible"))
    ]
    team_size = int(team_service.rules.rules["teams"][team]["size"])

    projected = apply_projected_ranking(rows, team_size)
    rows = projected["rows"]
    live_cut = projected["projected_cut_hoa"]
    eligible_cut = projected["eligible_cut_hoa"]

    selected = [
        row for row in rows
        if row["haa_qualified"] and bool(row.get("eligible"))
    ][:team_size]

    for row in rows:
        row["live_pool_rank"] = row["projected_rank"]
        row["live_team"] = row in selected
        row["live_cut_hoa"] = live_cut
        row["eligible_cut_hoa"] = eligible_cut
        row["live_gap_to_cut"] = row["gap_to_projected_cut"]

"""
    d=d[:start]+replacement+d[end:]
    d=d.replace('"live_cut_hoa": live_cut,\n', '"live_cut_hoa": live_cut,\n            "eligible_cut_hoa": eligible_cut,\n', 1)
    compile(d, str(DASH), "exec")
    DASH.write_text(d, encoding="utf-8")

    g=GUI.read_text(encoding="utf-8")
    imp2="from .eligibility_colors import EligibilityRowDelegate"
    anchor="from .live_dashboard import live_team_rows, live_dashboard_for_ata"
    if imp2 not in g:
        if anchor not in g:
            raise RuntimeError("Could not find live dashboard GUI import.")
        g=g.replace(anchor, anchor+"\n"+imp2, 1)

    old='        self.live_table.setAlternatingRowColors(True)\n        self.live_table.setSelectionBehavior(QAbstractItemView.SelectRows)\n'
    new='        self.live_table.setAlternatingRowColors(False)\n        self.live_table.setSelectionBehavior(QAbstractItemView.SelectRows)\n        self.live_table.setItemDelegate(EligibilityRowDelegate(self.live_table))\n'
    if "EligibilityRowDelegate(self.live_table)" not in g:
        if old not in g:
            raise RuntimeError("Could not find live table setup.")
        g=g.replace(old,new,1)

    g=g.replace('("live_pool_rank","Pool Rank"),', '("live_pool_rank","Projected Rank"),', 1)
    g=g.replace('("live_cut_hoa","Cut"),', '("live_cut_hoa","Projected Cut"),', 1)
    g=g.replace('("live_gap_to_cut","Gap"),', '("live_gap_to_cut","Gap to Projected Cut"),', 1)

    old2='        cut=summary["live_cut_hoa"]\n        cut_text="Not established" if cut is None else f"{cut:.2f}%"\n'
    new2='        cut=summary["live_cut_hoa"]\n        cut_text="Not established" if cut is None else f"{cut:.2f}%"\n        eligible_cut=summary.get("eligible_cut_hoa")\n        eligible_cut_text="Not established" if eligible_cut is None else f"{eligible_cut:.2f}%"\n'
    if old2 in g:
        g=g.replace(old2,new2,1)

    g=g.replace('            f"<b>Live cut:</b> {cut_text}<br>"', '            f"<b>Projected cut:</b> {cut_text} &nbsp;&nbsp; " \\n            f"<b>Eligible-now cut:</b> {eligible_cut_text}<br>"', 1)

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
    print("MNTrapTeam 3.3.0 applied: highest Live HOA first; green eligible, red incomplete.")

if __name__=="__main__":
    main()