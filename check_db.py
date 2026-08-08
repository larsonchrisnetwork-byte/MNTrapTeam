from mntrapteam.database import Database
from mntrapteam.paths import DATA

db = Database(DATA / "mntrapteam.db")

sql = """
SELECT
    COUNT(DISTINCT h.shooter_id) AS haa_qualified,
    COUNT(DISTINCT CASE
        WHEN lower(COALESCE(st.source,'')) LIKE 'myata%'
        THEN h.shooter_id
    END) AS with_myata
FROM haa_qualifications h
LEFT JOIN season_stats st
    ON st.shooter_id = h.shooter_id
   AND st.season = h.season
WHERE h.season = 2026
  AND h.verified = 1
"""

for row in db.query(sql):
    result = dict(row)
    result["missing_myata"] = (
        result["haa_qualified"] - result["with_myata"]
    )
    print(result)
