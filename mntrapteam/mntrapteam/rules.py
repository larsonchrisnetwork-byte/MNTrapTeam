from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from .paths import CONFIG

@dataclass(slots=True)
class EligibilityResult:
    eligible:bool; team:str; reasons:list[str]; progress:dict[str,tuple[int,int]]

    @property
    def missing_count(self)->int:
        return len(self.reasons)

    def deficits(self)->dict[str,int]:
        return {k:max(0,need-have) for k,(have,need) in self.progress.items() if need>have}

class RulesEngine:
    def __init__(self,path:Path=CONFIG/'mta_rules.json'):
        self.path=Path(path); self.rules=json.loads(self.path.read_text(encoding='utf-8'))
    def team_for_category(self,category:str|None)->str:
        c=(category or 'MEN').upper().replace('-','_').replace(' ','_')
        aliases={'LADY_I':'LADY','LADY_II':'LADY','SUB_VET':'MEN','SUBVET':'MEN','SENIOR_VET':'SR_VET','SENIOR_VETERAN':'SR_VET','SRVET':'SR_VET','SUB_JUNIOR':'SUB_JR','SUBJR':'SUB_JR','JUNIOR_GOLD':'JUNIOR'}
        return aliases.get(c,c if c in self.rules['teams'] else 'MEN')
    def check(self,row:dict,requested_team:str|None=None)->EligibilityResult:
        team=requested_team or self.team_for_category(row.get('category_declared') or row.get('category'))
        req=self.rules['teams'][team]; gen=self.rules['general']; reasons=[]; progress={}
        for d in ('singles','handicap','doubles'):
            have=int(row.get(f'{d}_targets') or 0); need=int(req[d]); progress[d]=(have,need)
            if have<need: reasons.append(f'{d.title()}: {have:,} of {need:,} total targets')
        for d in ('singles','handicap','doubles'):
            need=0 if team=='SUB_JR' and d=='doubles' else int(gen['in_state'][d]); have=int(row.get(f'mn_{d}_targets') or 0); progress[f'mn_{d}']=(have,need)
            if have<need: reasons.append(f'Minnesota {d}: {have:,} of {need:,} targets')
        junior=team in ('JUNIOR','SUB_JR'); clubs=int(row.get('mn_clubs') or 0)
        needclubs=0 if junior and gen.get('junior_club_exempt',True) else int(gen['clubs']); progress['clubs']=(clubs,needclubs)
        if clubs<needclubs: reasons.append(f'Minnesota clubs: {clubs} of {needclubs}')
        haa=bool(row.get('haa_complete')); progress['haa']=(int(haa),1)
        if gen.get('haa_required',True) and not haa: reasons.append('HAA not completed at resident MN Zone or MN State Shoot')
        if (row.get('state') or 'MN').upper()!='MN': reasons.append('Not marked as a Minnesota resident')
        return EligibilityResult(not reasons,team,reasons,progress)
