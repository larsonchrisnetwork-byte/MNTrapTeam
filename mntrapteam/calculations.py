def avg(hits, targets): return hits/targets*100 if targets else 0.0
def hoa(row): return (avg(row.get('singles_hits',0),row.get('singles_targets',0))+avg(row.get('handicap_hits',0),row.get('handicap_targets',0))+avg(row.get('doubles_hits',0),row.get('doubles_targets',0)))/3
def project(hits,targets,new_targets,new_average):
    new_hits=round(new_targets*new_average/100)
    return {'hits':hits+new_hits,'targets':targets+new_targets,'average':avg(hits+new_hits,targets+new_targets)}
def team_rankings(rows, rules_engine, team):
    out=[]
    for r in rows:
        if rules_engine.team_for_category(r.get('category_declared') or r.get('category'))!=team: continue
        e=rules_engine.check(r,team); x=dict(r); x['hoa']=hoa(r); x['eligible']=e.eligible; x['eligibility_reasons']='; '.join(e.reasons); out.append(x)
    out.sort(key=lambda x:(x['eligible'],x['hoa']),reverse=True)
    size=rules_engine.rules['teams'][team]['size']
    for i,x in enumerate(out,1): x['rank']=i; x['selected']=x['eligible'] and sum(1 for y in out[:i] if y['eligible'])<=size
    return out
