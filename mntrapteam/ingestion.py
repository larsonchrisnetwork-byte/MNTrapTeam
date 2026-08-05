
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
from .importers import OfficialStatsImporter, ScoreboardImporter, canonicalize, read_table

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".html", ".htm", ".pdf"}

def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def classify_file(path):
    dataframe = canonicalize(read_table(path))
    columns = set(dataframe.columns)
    totals = {"singles_targets","handicap_targets","doubles_targets"}
    results = {"singles_score","handicap_score","doubles_score","discipline","score"}
    averages_or_hits = {"singles_hits","handicap_hits","doubles_hits","singles_average","handicap_average","doubles_average"}
    if len(columns & totals) >= 2 and columns & averages_or_hits:
        return "official"
    if columns & results or {"name","targets","hits"} <= columns:
        return "scoreboard"
    return "unknown"

@dataclass
class ImportResult:
    path: Path
    kind: str
    rows_read: int = 0
    rows_imported: int = 0
    warnings: list[str] = field(default_factory=list)
    skipped_duplicate: bool = False
    error: str | None = None

class TrackedOfficialStatsImporter:
    def __init__(self, database):
        self.db = database
        self.importer = OfficialStatsImporter(database)

    def import_file(self, path, season):
        path = Path(path)
        digest = file_digest(path)
        if self.db.query("SELECT id FROM imports WHERE sha256=?", (digest,)):
            return 0, ["This exact file was already imported"]
        dataframe = canonicalize(read_table(path))
        imported, warnings = self.importer.import_file(path, season)
        self.db.execute(
            "INSERT INTO imports(filename,kind,sha256,rows_read,rows_imported,warnings) VALUES(?,?,?,?,?,?)",
            (path.name,"official",digest,len(dataframe),imported,"\n".join(warnings)),
        )
        return imported, warnings

class BatchImportService:
    def __init__(self, database, threshold=88):
        self.db = database
        self.threshold = threshold

    def discover(self, folder):
        folder = Path(folder)
        if not folder.is_dir():
            raise NotADirectoryError(folder)
        return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)

    def import_folder(self, folder, season, club="", shoot_date=None, in_state=True):
        results = []
        for path in self.discover(folder):
            result = ImportResult(path=path, kind="unknown")
            try:
                dataframe = canonicalize(read_table(path))
                result.rows_read = len(dataframe)
                result.kind = classify_file(path)
                if result.kind == "official":
                    imported, warnings = TrackedOfficialStatsImporter(self.db).import_file(path, season)
                elif result.kind == "scoreboard":
                    imported, warnings = ScoreboardImporter(self.db,self.threshold).import_file(
                        path, season, club=club, shoot_date=shoot_date, in_state=in_state
                    )
                else:
                    result.error = "Could not classify this file as official totals or a ShootScoreBoard report."
                    results.append(result)
                    continue
                result.rows_imported = imported
                result.warnings = warnings
                result.skipped_duplicate = imported == 0 and any("already imported" in w.lower() for w in warnings)
            except Exception as error:
                result.error = str(error)
            results.append(result)
        return results
