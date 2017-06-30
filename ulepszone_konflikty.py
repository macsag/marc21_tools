import requests
from pymarc import *
import csv

def normalizacja_ident(str):
    #usuwa kropki i spacje w całym polu

    str_out = ''.join(c.replace('.', '').replace(' ', '') for c in str) #usuwa wszystkie kropki i spacje w polu
    return str_out

def normalizacja_XXX(str):
    #usuwa kropki i spacje na końcu rekordu (obejmuje przypadki: '..', ' .', '  ', '. ', '.', ' ')

    if str[-1] in ('.', ' '):
        str_mid = str[:-1]
        if str_mid[-1] in ('.', ' '):
            str_out = str_mid[:-1]
        else:
            str_out = str_mid
    else:
        str_out = str
    return str_out

def do_slownika(fname, ident, pola_marc):
    #zamienia plik marc na słownik o postaci: {'nr rekordu': 'hasła główne rekordu'}
    #WAŻNE! wymaga zmodyfikowanej bibl. pymarc: niektóre błędy rekordów muszą być łapane już na poziomie biblioteki!

    dict_out = {}
    with open(fname, 'rb') as fp:
        reader = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')
        licznik = 0
        for record in reader:
            nr_rek = normalizacja_ident(record.get_fields(ident)[0].value()) #normalizacja usuwa ew. kropki i spacje z pola 035
            wartosci = {}
            for pole in pola_marc:
                try:
                    wartosci[pole] = normalizacja_XXX(record.get_fields(pole)[0].value())
                except IndexError as e:
                    wartosci[pole] = ''
            dict_out[nr_rek] = wartosci
            licznik += 1
            logging.debug('Dodałem do słownika: %s: %s', nr_rek, wartosci)
    logging.info('Przetworzono %s rekordy/ów z pliku %s', licznik, fname)
    return dict_out

def szukaj_konfliktu(pola_marc, csv_out, fname1='authorities-all.mrc', fname2='wzorcowe.mrc', ident1='001', ident2='035'):
    #główna funkcja: porównuje rekordy i szuka konfliktów

    dict1 = do_slownika(fname1, ident1, pola_marc)
    dict2 = do_slownika(fname2, ident2, pola_marc)

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
                niezgodne_wykaz[nr_rek] = rekord1 + rekord2
                licznik_niezgodne += 1
                logging.debug('Rekord %s niezgodny: %s', nr_rek, niezgodne_wykaz[nr_rek])
        else:
            logging.debug('Nie ma takiego rekordu.')
    wszystkie = licznik_niezgodne + licznik_zgodne
    logging.info("Przetworzono %s rekordy/ów: %s zgodne/ych, %s niezgodne/ych", wszystkie, licznik_zgodne, licznik_niezgodne)

    do_csv(csv_out, niezgodne_wykaz)

def do_csv(fnameout, raport):
    with open(fnameout, 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, dialect='excel')
        w.writerows(raport.items())

logging.root.addHandler(logging.StreamHandler(sys.stdout))
logging.root.setLevel(level=logging.DEBUG)

raporty_do_wygenerowania = ['100', '110', '111', '130', '150', '151', '155']
nazwy_raportow = ['rap100.csv', 'rap110.csv', 'rap111.csv', 'rap130.csv', 'rap150.csv', 'rap151.csv', 'rap155.csv']
szukaj_konfliktu(raporty_do_wygenerowania, nazwy_raportow)