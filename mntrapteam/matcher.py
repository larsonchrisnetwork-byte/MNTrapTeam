from rapidfuzz import fuzz, process
class ShooterMatcher:
    def __init__(self, db, threshold=88): self.db=db; self.threshold=threshold
    def match(self, raw_name, ata_number=None):
        if ata_number:
            rows=self.db.query('SELECT * FROM shooters WHERE ata_number=?',(str(ata_number).strip(),))
            if rows: return rows[0]['id'],100
        aliases=self.db.query('SELECT shooter_id FROM aliases WHERE upper(raw_name)=upper(?)',(raw_name,))
        if aliases: return aliases[0]['shooter_id'],100
        shooters=self.db.query('SELECT id,display_name FROM shooters')
        if not shooters: return None,0
        choices={r['display_name']:r['id'] for r in shooters}; found=process.extractOne(raw_name,choices.keys(),scorer=fuzz.token_sort_ratio)
        if found and found[1]>=self.threshold: return choices[found[0]],found[1]
        return None,found[1] if found else 0
