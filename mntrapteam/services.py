from pathlib import Path
import csv
import json
import webbrowser

from .calculations import team_rankings, hoa
from .paths import EXPORTS


class TeamService:
    def __init__(self, db, rules):
        self.db = db
        self.rules = rules

    def season_rows(self, season):
        rows = self.db.query(
            """
            SELECT s.*, st.*
            FROM shooters s
            JOIN season_stats st ON st.shooter_id = s.id
            WHERE st.season = ? AND s.active = 1
            """,
            (season,),
        )
        for row in rows:
            row["hoa"] = hoa(row)
            row["eligibility"] = self.rules.check(row)
        return rows

    def rankings(self, season, team):
        return team_rankings(self.season_rows(season), self.rules, team)

    def team_summary(self, season, team):
        rows = self.rankings(season, team)
        selected = [row for row in rows if row["selected"]]
        eligible = [row for row in rows if row["eligible"]]
        team_size = int(self.rules.rules["teams"][team]["size"])
        cut_line = selected[-1]["hoa"] if len(selected) == team_size else None
        return {
            "team": team,
            "team_size": team_size,
            "tracked": len(rows),
            "eligible": len(eligible),
            "selected": len(selected),
            "cut_line_hoa": cut_line,
            "open_positions": max(0, team_size - len(selected)),
        }

    def snapshot(self, season, label):
        payload = {
            team: self.rankings(season, team)
            for team in self.rules.rules["teams"]
        }
        self.db.execute(
            "INSERT INTO snapshots(season,label,payload) VALUES(?,?,?)",
            (season, label, json.dumps(payload, default=lambda value: value.__dict__)),
        )


class ExportService:
    def __init__(self, team_service):
        self.ts = team_service

    def csv_team(self, season, team):
        path = EXPORTS / f"{season}_{team}_standings.csv"
        rows = self.ts.rankings(season, team)
        keys = [
            "rank",
            "selected",
            "eligible",
            "display_name",
            "ata_number",
            "category",
            "hoa",
            "cut_line_hoa",
            "hoa_gap_to_cut",
            "birds_per_300_gap",
            "singles_targets",
            "handicap_targets",
            "doubles_targets",
            "mn_singles_targets",
            "mn_handicap_targets",
            "mn_doubles_targets",
            "mn_clubs",
            "eligibility_reasons",
        ]
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def xlsx_all(self, season):
        import pandas as pd

        path = EXPORTS / f"{season}_MN_State_Teams.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as workbook:
            for team in self.ts.rules.rules["teams"]:
                rows = self.ts.rankings(season, team)
                pd.DataFrame(rows).drop(
                    columns=["eligibility"], errors="ignore"
                ).to_excel(workbook, sheet_name=team, index=False)

            summaries = [
                self.ts.team_summary(season, team)
                for team in self.ts.rules.rules["teams"]
            ]
            pd.DataFrame(summaries).to_excel(
                workbook, sheet_name="Team Summary", index=False
            )
        return path

    def pdf_team(self, season, team):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        path = EXPORTS / f"{season}_{team}_standings.pdf"
        rows = self.ts.rankings(season, team)
        styles = getSampleStyleSheet()
        document = SimpleDocTemplate(str(path), pagesize=landscape(letter))
        data = [
            [
                "Rank",
                "Team",
                "Shooter",
                "ATA",
                "HOA",
                "Cut",
                "Gap",
                "S",
                "H",
                "D",
                "Eligible",
            ]
        ]
        for row in rows:
            cut = row.get("cut_line_hoa")
            gap = row.get("hoa_gap_to_cut")
            data.append(
                [
                    row["rank"],
                    "Yes" if row["selected"] else "",
                    row["display_name"],
                    row.get("ata_number") or "",
                    f"{row['hoa']:.2f}",
                    "" if cut is None else f"{cut:.2f}",
                    "" if gap is None else f"{gap:+.2f}",
                    row["singles_targets"],
                    row["handicap_targets"],
                    row["doubles_targets"],
                    "Yes" if row["eligible"] else "No",
                ]
            )
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        document.build(
            [
                Paragraph(
                    f"{season} Minnesota {team} State Team Standings",
                    styles["Title"],
                ),
                Spacer(1, 12),
                table,
            ]
        )
        return path


def open_shootata_login():
    webbrowser.open("https://shootata.com/Shooter-Information-Center")
