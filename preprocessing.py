from pymarc import *
import logging
from tqdm import tqdm


def importuj_deskryptory(baza_bn):
    initial_check_fields = ['100', '110', '111', '150', '151', '155']
    subfields_to_exlude = ['t', 'x', 'y', 'z']

    with open(baza_bn, 'rb') as fp:
        marc_reader = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')
        do_imp = 0
        odrzucone = 0
        chunk_to_write = []

        for deskryptor in tqdm(marc_reader):
            for marc_field in initial_check_fields:
                if marc_field in deskryptor:  # sprawdzaj, czy rekord należy do dozwolonego typu typu
                    nlp_id = deskryptor.get_fields('001')[0].value()
                    logging.debug('Rekord {} typu {}'.format(nlp_id, marc_field))
                    if deskryptor.get_fields(marc_field)[0].get_subfields(*subfields_to_exlude):
                        logging.debug('Rekord {} zawiera niedozwolone podpola. Pomijam.'.format(nlp_id))
                        odrzucone += 1
                        break
                    else:
                        chunk_to_write.append(deskryptor)
                        do_imp += 1
                        if do_imp % 500 == 0:
                            zapisz_do_mrc('20180521_pre_descriptors.marc', chunk_to_write)
                            chunk_to_write = []
                        break

        if chunk_to_write != 0:
            zapisz_do_mrc('20180521_pre_descriptors.mrc', chunk_to_write)

    return do_imp, odrzucone


def zapisz_do_mrc(plik_wynikowy, rekordy_do_zapisu):
    with open(plik_wynikowy, 'ab') as fp:
        marc_writer = MARCWriter(fp)
        for rekord in rekordy_do_zapisu:
            marc_writer.write(rekord)


if __name__ == '__main__':

    logging.root.addHandler(logging.StreamHandler(sys.stdout))
    logging.root.setLevel(level=logging.ERROR)

    wynik = importuj_deskryptory('authorities-all.marc')
    print(wynik)