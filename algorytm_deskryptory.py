from pymarc import *
import logging

"""
Algorytm importu deskryptorów do bazy danych OMNIS:

wersja: 0.1
"""

#  wariant A: import z bazy danych Biblioteki Narodowej

def importuj_deskryptory(baza_bn):
    initial_check_fields = ['100', '110', '111', '130', '150', '151', '155']
    subfields_to_exlude = ['x', 'y', 'z']

    with open(baza_bn, 'rb') as fp:
        marc_reader = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')

        for deskryptor in marc_reader:
            for marc_field in initial_check_fields:
                if marc_field in deskryptor:  # sprawdzaj, czy rekord należy do dozwolonego typu typu
                    nlp_id = deskryptor.get_fields('001')[0].value()
                    logging.debug('Rekord {} typu {}'.format(nlp_id, marc_field))
                    if deskryptor.get_fields(marc_field)[0].get_subfields(*subfields_to_exlude):
                        logging.debug('Rekord {} zawiera niedozwolone podpola. Pomijam.'.format(nlp_id))
                        break
                    else:
                        skonwertuj_rekord()
                        zaimportuj_rekord()
                        break


def skonwertuj_rekord():
    logging.debug('Konwertuję...')


def zaimportuj_rekord():
    logging.debug("Importuję...")


if __name__ == '__main__':

    logging.root.addHandler(logging.StreamHandler(sys.stdout))
    logging.root.setLevel(level=logging.DEBUG)

    importuj_deskryptory('authorities-all.marc')