import requests
import json
import time
from pymarc import MARCReader, Field

fname = 'marc21.dat'
fnameout = 'marc21out.dat'

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
