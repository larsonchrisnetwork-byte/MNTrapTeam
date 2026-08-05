from mntrapteam.calculations import avg,project
def test_avg(): assert avg(95,100)==95
def test_project(): assert project(950,1000,1000,97)['average']==96
