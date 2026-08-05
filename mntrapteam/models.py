from dataclasses import dataclass
@dataclass(slots=True)
class DisciplineStat:
    hits:int=0; targets:int=0
    @property
    def average(self): return (self.hits/self.targets*100) if self.targets else 0.0
@dataclass(slots=True)
class ShooterSeason:
    shooter_id:int; name:str; ata_number:str=''; category:str='MEN'; state:str='MN'
    singles:DisciplineStat=DisciplineStat(); handicap:DisciplineStat=DisciplineStat(); doubles:DisciplineStat=DisciplineStat()
    mn_singles:int=0; mn_handicap:int=0; mn_doubles:int=0; mn_clubs:int=0; haa_complete:bool=False
    @property
    def hoa(self): return (self.singles.average+self.handicap.average+self.doubles.average)/3
