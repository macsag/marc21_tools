import csv
from tqdm import tqdm
from pymarc import *


def load_and_select_from_viaf(viaf_input_file, siglum='NLP', data_dump=False):
    # selects ids from viaf; for NLP use 'NLP' (default) / for NUKAT use 'NUKAT|'

    selected_viaf_ids = []

    with open(viaf_input_file, encoding='utf-8') as fp_in:
            for line in tqdm(fp_in, desc='Przetwarzam plik viaf'):
                viaf, local = line.split('\t')
                length = len(siglum)
                if siglum in local[:length]:
                    selected_viaf_ids.append((local.split('|')[1][:-1], viaf))

    if data_dump:
        dump_to_tsv(selected_viaf_ids, 'viup_selected_viaf.tsv')

    return selected_viaf_ids


def load_and_select_from_catalogue(catalogue_input_file):
    # creates 2 dictionaries: with all local ids and selected local ids

    selected_local_ids = {}
    all_ids = {}

    with open(catalogue_input_file, 'rb') as fp:
        rdr = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')
        for rcd in tqdm(rdr, total=2200000, desc='Pobieram dane z katalogu'):
            try:
                loc_id = rcd.get_fields('001')[0].value()
            except IndexError:
                continue
            if rcd.get_fields('024'):
                selected_local_ids[loc_id] = rcd.get_fields('024')[0].value()[:-4]
                all_ids[loc_id] = None
            else:
                all_ids[loc_id] = None

    result = [all_ids, selected_local_ids]

    return result


def catalogue_lookup(list_to_check, all_ids, selected_ids, out_file):

    list_to_update = []
    list_of_invalid_ids = []

    for item in tqdm(list_to_check, desc='Sprawdzam w katalogu'):
        if item[0] not in all_ids:
            list_of_invalid_ids.append(item)
        elif item[0] not in selected_ids:
            item = ('001  ' + item[0], '0247 |a' + item[1] + '|2viaf', '996  |a.' + item[0])
            list_to_update.append(item)

    dump_to_tsv(list_to_update, out_file)
    #dump_to_tsv(list_of_invalid_ids, 'viup_invalid_09102017.tsv')


def dump_to_tsv(data_to_dump, output_file):

    with open(output_file, 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t')
        w.writerows(data_to_dump)


if __name__ == '__main__':

    viaf_file = 'viaf-20171001-links.txt'
    loc_file = 'authorities-all.marc'
    out = 'viup_to_update_09102017.tsv'

    loaded_from_viaf = load_and_select_from_viaf(viaf_file)
    loaded_from_catalogue = load_and_select_from_catalogue(loc_file)
    catalogue_lookup(loaded_from_viaf, loaded_from_catalogue[0], loaded_from_catalogue[1])
