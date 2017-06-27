from marc_tools import *
import time

# konfiguracja

# pliki do porównania
fname1 = 'authorities-all.mrc'
fname2 = 'wzorcowe.mrc'

# pola do identyfikacji rekordów (odpowiednio w 1. i 2. pliku)
ident1 = '001'
ident2 = '035'

# pole do sprawdzania
pole_marc = '155'

# czy stosować normalizację_XXX (usuwanie kropek i spacji z końca rekordu)?
use_normalizacja = True

# pliki wyjściowe z niezgodnymi rekordami
fnameout1 = 'konflikty-raport.csv'
fnameout2 = 'konflikty-marc.mrc'

# plik z logami
log = 'konflikty-log.txt'

# koniec konfiguracji

file = open(log, 'a', encoding='utf-8')
logging.root.addHandler(logging.StreamHandler(file))
logging.root.setLevel(level=logging.DEBUG)


begin = time.time()
raport = szukaj_konfliktu(fname1, fname2, ident1, ident2, pole_marc, fnameout1)
print('Czas generowania raportu', time.time() - begin)



