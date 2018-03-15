import csv
import logging
import sys
from tqdm import tqdm
from pymarc import *


def load_and_select_from_viaf(viaf_input_file, siglum='NLP', data_dump=False):
    """selects ids from viaf;
        for NLP use siglum='NLP' (default) / for NUKAT use siglum='NUKAT|';
        returns a list of tuples (local_id, viaf_id)"""

    selected_viaf_ids = []

    with open(viaf_input_file, encoding='utf-8') as fp:
            for line in tqdm(fp, desc='Przetwarzam plik viaf'):
                viaf_id, local_id = line.split('\t')
                if siglum in local_id[:len(siglum)]:
                    selected_viaf_ids.append((local_id.split('|')[1][:-1], viaf_id))

    logging.info('Znaleziono {} rekordów VIAF z identyfikatorem {}'.format(len(selected_viaf_ids), siglum))

    if data_dump:
        dump_to_tsv(selected_viaf_ids, 'viaf_selected_viaf_ids.tsv')

    return selected_viaf_ids


def load_and_select_from_catalogue(catalogue_input_file):
    """creates 2 dictionaries: with all local ids and selected local ids (with viaf id);
        returns tuple (dictionary of all local ids, dictionary of selected local ids)"""

    selected_local_ids = {}
    all_ids = {}

    with open(catalogue_input_file, 'rb') as fp:
        rdr = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')

        prev_rcd_id = ''
        for rcd in tqdm(rdr, desc='Pobieram dane z katalogu'):
            try:
                loc_id = rcd.get_fields('001')[0].value()
                all_ids[loc_id] = None
                prev_rcd_id = loc_id
            except IndexError:
                logging.error('Błąd! Pusty rekord. Poprzedni numer rekordu: {}'.format(prev_rcd_id))
                continue
            if rcd.get_fields('024'):
                selected_local_ids[loc_id] = rcd.get_fields('024')[0].value()[:-4]

    return all_ids, selected_local_ids


def catalogue_lookup(list_to_check, all_ids, selected_ids, out_update_file, out_invalid_file):
    """checks if loc_id from viaf exists in local catalogue; if exists and lacks viaf id, adds it and dumps to tsv;
        produces 2 files: file to update and file with invalid ids"""

    list_to_update = []
    list_of_invalid_ids = []

    for item in tqdm(list_to_check, desc='Sprawdzam w katalogu'):
        if item[0] not in all_ids:
            list_of_invalid_ids.append(item)
        if item[0] not in selected_ids and item[0] in all_ids:
            item_prepared = ('001  ' + item[0], '0247 |a' + item[1] + '|2viaf', '996  |a.' + item[0])
            list_to_update.append(item_prepared)

    dump_to_tsv(list_to_update, out_update_file)
    dump_to_tsv(list_of_invalid_ids, out_invalid_file)


def dump_to_tsv(data_to_dump, output_file):

    with open(output_file, 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t')
        w.writerows(data_to_dump)


def main_workflow(viaf_file, loc_file, to_update_file, invalid_file):
    loaded_from_viaf = load_and_select_from_viaf(viaf_file)
    loaded_from_catalogue = load_and_select_from_catalogue(loc_file)
    catalogue_lookup(loaded_from_viaf, loaded_from_catalogue[0], loaded_from_catalogue[1], to_update_file, invalid_file)


if __name__ == '__main__':

    logging.root.addHandler(logging.StreamHandler(sys.stdout))
    logging.root.setLevel(level=logging.DEBUG)

    # configs for main_workflow
    viaf_file = 'viaf-20180307-links.txt'
    loc_file = 'authorities-all.marc'
    out_file_to_update = 'viaf_to_update_20180307.tsv'
    out_file_invalid_ids = 'viaf_invalid_ids_20180307.tsv'

    main_workflow(viaf_file, loc_file, out_file_to_update, out_file_invalid_ids)
