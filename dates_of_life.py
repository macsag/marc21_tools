from pymarc import *


def add_dates_of_life(fname_in, fname_out):
    # funkcja uzupełniająca daty życia w polu 046 na podstawie |d pola 100
    # nie uwzględnia współwystępowania z innymi podpolami (brak nawiasów)
    # nie uwzględnia normalizacji dat do ISO 8601
    # nie uwzględnia mapowania określeń w jezyku naturalnym do oznaczeń edtf (np. 'ok.' do '~' itp.)
    # nie uwzględnia wielu innych rzeczy

    with open(fname_in, 'rb') as fp:
        rdr = MARCReader(fp)
        for rec in rdr:
            if rec['100']:
                if rec['100']['d']:
                    dates = rec['100']['d']
                    logging.debug('Daty życia: {}'.format(dates))
                    date_of_birth = dates[1:].split('-')[0]
                    date_of_death = dates[1:len(dates) - 1].split('-')[1]
                    rec.add_ordered_field(
                        Field(tag='046', indicators=[' ', ' '], subfields=['f', date_of_birth, 'g', date_of_death]))
                    out = open(fname_out, 'ab')
                    out.write(rec.as_marc())
                    out.close()
                else:
                    logging.debug('Brak podpola |d.')


if __name__ == '__main__':

    logging.root.addHandler(logging.StreamHandler(sys.stdout))
    logging.root.setLevel(level=logging.DEBUG)

    add_dates_of_life('authorities-all.marc', 'authorities-date-added.marc')
