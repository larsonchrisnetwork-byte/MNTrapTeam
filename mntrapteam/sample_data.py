SAMPLE=[
('1000001','Alex Anderson','MEN',1500,1460,1260,1121,1150,1080,700,700,500,4,1),
('1000002','Blake Benson','MEN',2200,2112,1800,1656,1600,1504,900,800,700,5,1),
('1000003','Casey Carlson','MEN',2000,1900,1600,1422,1700,1555,800,750,800,4,1),
('1000004','Dana Davis','LADY',1500,1430,1200,1080,900,830,800,700,500,4,1),
('1000005','Evan Erickson','VET',1400,1344,1100,990,800,752,800,700,500,5,1),
('1000006','Frank Foster','SR_VET',1300,1222,900,801,600,552,750,700,400,4,1),
('1000007','Grace Green','JUNIOR',1300,1250,1000,920,600,570,800,700,450,1,1),
('1000008','Henry Hall','SUB_JR',1200,1150,900,820,0,0,800,700,0,1,1),
]
def load(db,season=2026):
    for x in SAMPLE:
        ata,name,cat,st,sh,ht,hh,dt,dh,mns,mnh,mnd,clubs,haa=x
        sid=db.upsert_shooter(ata,name,cat)
        db.upsert_stats(sid,season,singles_targets=st,singles_hits=sh,handicap_targets=ht,handicap_hits=hh,doubles_targets=dt,doubles_hits=dh,mn_singles_targets=mns,mn_handicap_targets=mnh,mn_doubles_targets=mnd,mn_clubs=clubs,haa_complete=haa,category_declared=cat,source='sample')
