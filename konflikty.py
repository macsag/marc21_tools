from pymarc import *
import csv
import time

#konfiguracja

#pliki do porównania
fname1 = 'authorities-allv2.mrc'
fname2 = 'wzorcowev2.mrc'

#pola do identyfikacji rekordów (odpowiednio w 1. i 2. pliku)
ident1 = '001'
ident2 = '035'

#pole do sprawdzania
pole_marc = '155'

#czy stosować normalizację_100?
use_normalizacja = True

#pliki wyjściowe z niezgodnymi rekordami
fnameout1 = 'konflikty-raport.csv'
fnameout2 = 'konflikty-marc.mrc'

#plik z logami
log = 'konflikty-log.txt'

#koniec konfiguracji

def normalizacja_ident(str):
    #usuwa kropki i spacje w całym polu

    str_out = ''.join(c.replace('.', '').replace(' ', '') for c in str) # usuwa wszystkie kropki i spacje
    return str_out

def normalizacja_100(str):
    #usuwa kropki i spacje na końcu rekordu

    if str[-1] in ('.', ' '):
        str_mid = str[:-1]
        if str_mid[-1] in ('.', ' '):
            str_out = str_mid[:-1]
        else:
            str_out = str_mid
    else:
        str_out = str
    return str_out

def do_slownika(fname, ident, pole_marc, use_normalizacja=True):
    #zamienia plik marc na słownik o postaci: {'nr rekordu': 'rekord'}

    dict_out = {}
    with open(fname, 'rb') as fp:
        reader = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')
        licznik = 0
        for record in reader:
            try:
                nr_rek = normalizacja_ident(record.get_fields(ident)[0].value()) #normalizacja usuwa ew. kropki i spacje z pola 035
                if use_normalizacja:
                    wartosci = {pole_marc: [normalizacja_100(v.value()) for v in record.get_fields(pole_marc)]}
                else:
                    wartosci = {pole_marc: [(v.value()) for v in record.get_fields(pole_marc)]}
                dict_out[nr_rek] = wartosci
                licznik += 1
                logging.debug('Dodałem do słownika: %s: %s', nr_rek, dict_out.get(nr_rek))
            except Exception as error:
                logging.error('Błąd przetwarzania rekordu: %s', error)
    logging.info('Przetworzono %s rekordy/ów z pliku %s', licznik, fname)
    return dict_out

def szukaj_konfliktu(fname1, fname2, ident1, ident2, pole_marc, csv_out='raport-csv.csv', marc_out='raport-marc.mrc'):
    #główna funkcja: porównuje rekordy i szuka konfliktów

    dict1 = do_slownika(fname1, ident1, pole_marc)
    dict2 = do_slownika(fname2, ident2, pole_marc)

    niezgodne_wykaz = {}
    licznik_zgodne = 0
    licznik_niezgodne = 0

    for nr_rek in dict1:
        rekord2 = dict2.get(nr_rek)
        if rekord2 is not None:
            rekord1 = dict1.get(nr_rek)
            if rekord1 == rekord2:
                logging.debug('Rekord %s zgodny.', nr_rek)
                licznik_zgodne += 1
            else:
                niezgodne_wykaz[nr_rek] = rekord1[pole_marc] + rekord2[pole_marc]
                licznik_niezgodne += 1
                logging.debug('Rekord %s niezgodny: %s', nr_rek, niezgodne_wykaz[nr_rek])
            #todo
        else:
            logging.debug('Nie ma takiego rekordu.')
    wszystkie = licznik_niezgodne + licznik_zgodne
    logging.info("Przetworzono %s rekordy/ów: %s zgodne/ych, %s niezgodne/ych", wszystkie, licznik_zgodne, licznik_niezgodne)

    do_csv(csv_out, niezgodne_wykaz)

def do_csv(fnameout, raport):
    with open(fnameout, 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp)
        w.writerows(raport.items())

def do_marc(fname_in, fname_out, raport):
    with open(fname1, 'rb') as fp:
        reader = MARCReader(fp)
        licznik = 0
        for record in reader:
            licznik += 1
            if record['001'].value() not in raport:
                print('Brak.')
            else:
                print('Dodaję do pliku.')
                record.add_ordered_field(
                    Field(tag='997', indicators=[' ', ' '], subfields=['a', 'mod']))
                out = open(fnameout2, 'ab')
                out.write(record.as_marc())
                out.close()

#file = open(log, 'a', encoding='utf-8')
logging.root.addHandler(logging.StreamHandler(sys.stdout))
logging.root.setLevel(level=logging.DEBUG)

if __name__ == '__main__':
    begin = time.time()
    raport = szukaj_konfliktu(fname1, fname2, ident1, ident2, pole_marc, fnameout1)
    print('Czas generowania raportu', time.time() - begin)
