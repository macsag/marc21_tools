from marc_tools import *
import time

# konfiguracja

# pliki do porównania
fname1 = 'authorities-allv2.mrc'
fname2 = 'wzorcowev2.mrc'

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

#file = open(log, 'a', encoding='utf-8')
logging.root.addHandler(logging.StreamHandler(sys.stdout))
logging.root.setLevel(level=logging.DEBUG)


begin = time.time()
#szukaj_konfliktu(fname1, fname2, ident1, ident2, pole_marc, fnameout1)


raporty_do_wygenerowania = ['100', '110', '111', '130', '150', '151', '155']
nazwy_raportow = ['rap100.csv', 'rap110.csv', 'rap111.csv', 'rap130.csv', 'rap150.csv', 'rap151.csv', 'rap155.csv']

for field, raport in zip(raporty_do_wygenerowania, nazwy_raportow):
    print('Generuję raport o: ' + field)
    szukaj_konfliktu(pole_marc=field, csv_out=raport)

print('Czas generowania raportu', time.time() - begin)




