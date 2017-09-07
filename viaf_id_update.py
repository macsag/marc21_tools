import csv
from tqdm import tqdm
from pymarc import *


def load_and_select_from_viaf(viaf_input_file, data_dump=False):

    selected_viaf_ids = []

    with open(viaf_input_file, encoding='utf-8') as fp_in:
            for line in tqdm(fp_in, total=81209613, desc='Przetwarzam plik viaf'):
                viaf, local = line.split('\t')
                if 'NLP' in local[:3]:
                    selected_viaf_ids.append((local.split('|')[1][:-1], viaf))

    if data_dump:
        dump_to_tsv(selected_viaf_ids, 'selected_viaf.tsv')

    return selected_viaf_ids


def load_and_select_from_catalogue(catalogue_input_file, data_dump=False):

    selected_local_ids = {}

    with open(catalogue_input_file, 'rb') as fp:
        reader = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')
        for record in tqdm(reader, total=2200000, desc='Pobieram dane z katalogu'):
            if record.get_fields('024'):
                selected_local_ids[record.get_fields('001')[0].value()] = record.get_fields('024')[0].value()[:-4]

    if data_dump:
        dump_to_tsv(selected_local_ids, 'selected_local.tsv')

    return selected_local_ids


def catalogue_lookup(list_to_check, catalogue):

    list_to_update = []

    for item in tqdm(list_to_check, desc='Sprawdzam w API'):
        if item[0] not in catalogue:
            list_to_update.append(item)

    dump_to_tsv(list_to_update, 'viaf_id_to_update.tsv')


def dump_to_tsv(data_to_dump, output_file):

    with open(output_file, 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t')
        w.writerows(data_to_dump)


def make_marc_file(data):

    with open('viaf_to_update', 'rb') as fp:
        reader = MARCReader(fp)
        for record in reader:
                record.add_ordered_field(
                    Field(tag='046', indicators=[' ', ' '], subfields=['f', date_of_birth, 'g', date_of_death]))
                out = open(fnameout, 'ab')
                out.write(record.as_marc())
                out.close()


loaded_from_viaf = load_and_select_from_viaf('viaf-20170806-links.txt')
loaded_from_catalogue = load_and_select_from_catalogue('authorities-all.mrc')
catalogue_lookup(loaded_from_viaf, loaded_from_catalogue)
