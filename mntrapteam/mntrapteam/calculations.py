from __future__ import annotations
from dataclasses import dataclass

DISCIPLINES=('singles','handicap','doubles')

def average(hits:int|float, targets:int|float)->float:
    return (float(hits)/float(targets)*100.0) if targets else 0.0

def hoa(row:dict)->float:
    """MTA team HOA: arithmetic mean of singles, handicap and doubles averages."""
    return sum(average(row.get(f'{d}_hits',0),row.get(f'{d}_targets',0)) for d in DISCIPLINES)/3.0

def project(hits:int, targets:int, new_targets:int, new_average:float)->dict:
    if new_targets<0 or not 0<=new_average<=100: raise ValueError('Invalid projection values')
    new_hits=round(new_targets*new_average/100.0)
    return {'hits':hits+new_hits,'targets':targets+new_targets,'average':average(hits+new_hits,targets+new_targets),'added_hits':new_hits}

def targets_needed_for_average(hits:int,targets:int,goal:float,future_average:float,max_targets:int=100000)->int|None:
    if not 0<=goal<=100 or not 0<=future_average<=100: raise ValueError('Averages must be 0-100')
    if average(hits,targets)>=goal:return 0
    if future_average<=goal:return None
    # ceil((goal*T - H)/(future-goal)), expressed as proportions
    import math
    n=math.ceil((goal*targets-100*hits)/(future_average-goal))
    n=max(0,n)
    return n if n<=max_targets else None

def team_rankings(rows:list[dict],rules_engine,team:str)->list[dict]:
    out=[]
    for row in rows:
        if rules_engine.team_for_category(row.get('category_declared') or row.get('category'))!=team: continue
        result=rules_engine.check(row,team)
        x=dict(row); x['hoa']=hoa(row); x['eligible']=result.eligible; x['eligibility_reasons']='; '.join(result.reasons)
        out.append(x)
    out.sort(key=lambda x:(not x['eligible'], -x['hoa'], x.get('display_name','').lower()))
    size=int(rules_engine.rules['teams'][team]['size']); eligible_position=0
    for rank,x in enumerate(out,1):
        x['rank']=rank
        if x['eligible']: eligible_position+=1
        x['eligible_rank']=eligible_position if x['eligible'] else None
        x['selected']=bool(x['eligible'] and eligible_position<=size)
    return out


def hoa_gap_to_goal(row:dict, goal:float)->float:
    """Return percentage-point HOA improvement needed to reach goal."""
    if not 0 <= goal <= 100:
        raise ValueError('Goal must be 0-100')
    return max(0.0, goal - hoa(row))

def projected_hoa(row:dict, additions:dict[str,tuple[int,float]])->dict:
    """Project all three discipline averages and HOA.

    additions maps discipline to (new_targets, expected_average).
    """
    averages={}
    totals={}
    for d in DISCIPLINES:
        nt,na=additions.get(d,(0,0.0))
        pr=project(int(row.get(f'{d}_hits',0) or 0),int(row.get(f'{d}_targets',0) or 0),int(nt),float(na))
        averages[d]=pr['average']; totals[d]=pr
    return {'averages':averages,'disciplines':totals,'hoa':sum(averages.values())/3.0}

def eligibility_completion(progress:dict[str,tuple[int,int]])->float:
    """Weighted requirement completion percentage, capped at 100%."""
    ratios=[]
    for have,need in progress.values():
        if need <= 0: continue
        ratios.append(min(1.0, max(0.0, float(have)/float(need))))
    return (sum(ratios)/len(ratios)*100.0) if ratios else 100.0
