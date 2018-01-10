from pymarc import *
import logging
import sys


def show_field(catalogue_input_file, field, limit=None):

    with open(catalogue_input_file, 'rb') as fp:
        marc_reader = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')
        i = 1
        prev_id = ''
        for auth in marc_reader:
            if i == limit:
                break
            try:
                local_id = auth.get_fields('001')[0].value()
                prev_id = local_id
            except IndexError:
                logging.error('Błąd indeksowania. Brak numeru rekordu. Poprzedni numer: {}'.format(prev_id))
                continue
            if auth.get_fields(field):
                try:
                    body = auth.get_fields(field)
                    body_values = []
                    for value in body:
                        body_values.append(str(value))
                    to_show = '{} {}'.format(local_id, body_values)
                    logging.info(to_show)
                except IndexError:
                    logging.error('Brak pola {} w rekordzie nr {}'.format(field, local_id))
                    continue

if __name__ == '__main__':

    logging.root.addHandler(logging.StreamHandler(sys.stdout))
    logging.root.setLevel(level=logging.DEBUG)

    show_field('authorities-all.marc', '043')