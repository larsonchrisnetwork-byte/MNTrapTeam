from __future__ import annotations
import json
from dataclasses import dataclass
from .paths import CONFIG

@dataclass
class EligibilityResult:
    eligible: bool; team:str; reasons:list[str]; progress:dict

class RulesEngine:
    def __init__(self, path=CONFIG/'mta_rules.json'):
        self.rules=json.loads(path.read_text(encoding='utf-8'))
    def team_for_category(self, category:str):
        c=(category or 'MEN').upper().replace('-','_').replace(' ','_')
        aliases={'LADY_I':'LADY','LADY_II':'LADY','SUB_VET':'MEN','SENIOR_VET':'SR_VET','SRVET':'SR_VET','SUB_JUNIOR':'SUB_JR','JUNIOR_GOLD':'JUNIOR'}
        return aliases.get(c,c if c in self.rules['teams'] else 'MEN')
    def check(self, row:dict, requested_team=None):
        team=requested_team or self.team_for_category(row.get('category_declared') or row.get('category'))
        req=self.rules['teams'][team]; gen=self.rules['general']; reasons=[]; progress={}
        for d,col in [('singles','singles_targets'),('handicap','handicap_targets'),('doubles','doubles_targets')]:
            have=int(row.get(col) or 0); need=int(req[d]); progress[d]=(have,need)
            if have<need: reasons.append(f'{d.title()}: {have:,} of {need:,} total targets')
        for d,col in [('singles','mn_singles_targets'),('handicap','mn_handicap_targets'),('doubles','mn_doubles_targets')]:
            need=0 if team=='SUB_JR' and d=='doubles' else gen['in_state'][d]; have=int(row.get(col) or 0); progress['mn_'+d]=(have,need)
            if have<need: reasons.append(f'Minnesota {d}: {have:,} of {need:,} targets')
        junior=team in ('JUNIOR','SUB_JR')
        clubs=int(row.get('mn_clubs') or 0); needclubs=0 if junior and gen['junior_club_exempt'] else gen['clubs']; progress['clubs']=(clubs,needclubs)
        if clubs<needclubs: reasons.append(f'Minnesota clubs: {clubs} of {needclubs}')
        haa=bool(row.get('haa_complete')); progress['haa']=(int(haa),1)
        if gen['haa_required'] and not haa: reasons.append('HAA not completed at resident MN Zone or MN State Shoot')
        if (row.get('state') or 'MN').upper()!='MN': reasons.append('Not marked as a Minnesota resident')
        return EligibilityResult(not reasons,team,reasons,progress)
