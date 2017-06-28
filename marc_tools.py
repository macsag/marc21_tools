import requests
from pymarc import *
import csv

def dates_of_life(fname_in, fname_out):
    #niedokończona funkcja uzupełniająca daty życia w polu 046 na podstawie |d pola 100

    r = requests.get('http://data.bn.org.pl/api/authorities.marc?kind=person&sinceId=100&limit=100')

    with open(fname, 'wb') as fp:
        for chunk in r.iter_content(chunk_size=128):
            fp.write(chunk)

    with open(fname, 'rb') as fp:
        reader = MARCReader(fp)
        for record in reader:
            if record['100']['d'] == None:
                print('Brak podpola |d')
            else:
                dates = record['100']['d']
                print(dates)
                date_of_birth = dates[1:].split('-')[0]
                date_of_death = dates[1:len(dates) - 1].split('-')[1]
                record.add_ordered_field(
                    Field(tag='046', indicators=[' ', ' '], subfields=['f', date_of_birth, 'g', date_of_death]))
                out = open(fnameout, 'ab')
                out.write(record.as_marc())
                out.close()

#funkcje używane do znajdowania konfliktów

def normalizacja_ident(str):
    #usuwa kropki i spacje w całym polu

    str_out = ''.join(c.replace('.', '').replace(' ', '') for c in str) #usuwa wszystkie kropki i spacje
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

def do_slownika(fname, ident, pole_marc, use_normalizacja=True):
    #zamienia plik marc na słownik o postaci: {'nr rekordu': 'wybrane pola rekordu'}
    #WAŻNE! wymaga zmodyfikowanej bibl. pymarc: niektóre błędy rekordów muszą być łapane już na poziomie biblioteki!

    dict_out = {}
    with open(fname, 'rb') as fp:
        reader = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')
        licznik = 0
        for record in reader:
            try:
                nr_rek = normalizacja_ident(record.get_fields(ident)[0].value()) #normalizacja usuwa ew. kropki i spacje z pola 035
                if use_normalizacja:
                    wartosci = {pole_marc: [normalizacja_XXX(v.value()) for v in record.get_fields(pole_marc)]}
                else:
                    wartosci = {pole_marc: [(v.value()) for v in record.get_fields(pole_marc)]}
                dict_out[nr_rek] = wartosci
                licznik += 1
                logging.debug('Dodałem do słownika: %s: %s', nr_rek, dict_out.get(nr_rek))
            except Exception as error:
                logging.error('Błąd przetwarzania rekordu: %s', error)
    logging.info('Przetworzono %s rekordy/ów z pliku %s', licznik, fname)
    return dict_out

def szukaj_konfliktu(fname1='authorities-all.mrc', fname2='wzorcowe.mrc', ident1='001', ident2='035', pole_marc='', csv_out='raport-csv.csv'):
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
        else:
            logging.debug('Nie ma takiego rekordu.')
    wszystkie = licznik_niezgodne + licznik_zgodne
    logging.info("Przetworzono %s rekordy/ów: %s zgodne/ych, %s niezgodne/ych", wszystkie, licznik_zgodne, licznik_niezgodne)

    do_csv(csv_out, niezgodne_wykaz)

def do_csv(fnameout, raport):
    with open(fnameout, 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, dialect='excel')
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