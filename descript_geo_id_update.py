from pymarc import *
from marc_tools import normalizacja_XXX
from marc_tools import normalizacja_ident
import re
import csv
from SPARQLWrapper import SPARQLWrapper, JSON


class GeoAuthority(object):
    # wrapper around full MARC record
    def __init__(self, nr_bn, nat_lang_id, full_record):
        self.nr_bn = nr_bn
        self.nat_lang_id = nat_lang_id
        self.full_record = full_record

        self.viaf_id = None
        self.wikidata_id = None
        self.geonames_id = None

        self.type = None
        self.coordinates = None
        self.short_name = None

        self.country_or_settlement = None
        self.woj = None
        self.pow = None
        self.gm = None
        self.other_admin_units = None

        self.attribs_368 = None
        self.attribs_nl = []

        self.wikidata_entities = []
        self.wikidata_entities_to_disambiguate = None

    def get_attr_from_nat_lang_id(self):
        # transforms 151 field into a set of atomised properties: parses data from 'semi-natural' language

        if ' (' in self.nat_lang_id:  # checks for apposition
            self.short_name = reverse_name(self.nat_lang_id.split(' (')[0])
            do_apposition_heuristics(self)
            do_short_name_heuristics(self)
        else:
            self.short_name = reverse_name(self.nat_lang_id)
            do_short_name_heuristics(self)

    def get_attr_from_368_field(self):
        try:
            self.attribs_368 = self.full_record.get_fields('368')[0].get_subfields('b')
        except IndexError:
            pass

    def get_entities_from_wikidata(self):
        # gets all wikidata entities matching the short_name: SPARQL query against Wikidata endpoint

        logging.debug(self.short_name)
        sparql = SPARQLWrapper("https://query.wikidata.org/sparql")

        sparql.setQuery("""
            SELECT distinct ?item ?geonames ?viaf ?instof ?instofLabel ?adminunitLabel ?countryLabel WHERE{
                ?item ?label \"""" + self.short_name + """\"@pl.
                OPTIONAL { ?item wdt:P1566 ?geonames. }
                OPTIONAL { ?item wdt:P214 ?viaf. }
                OPTIONAL { ?item wdt:P31 ?instof. }
                OPTIONAL { ?item wdt:P131 ?adminunit. }
                OPTIONAL { ?item wdt:P17 ?country. }
                SERVICE wikibase:label { bd:serviceParam wikibase:language "pl"  }
                }
            """)

        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()['results']['bindings']
        temp_ids = []
        for res in results:  # does some claeaning and deduplication
            try:
                if 'wikidata' in res['item']['value'] and\
                   'strona ujednoznaczniająca' not in res['instofLabel']['value'] and\
                   res['item']['value'] not in temp_ids:
                    self.wikidata_entities.append(res)
                    temp_ids.append(res['item']['value'])
            except KeyError:
                if res['item']['value'] not in temp_ids:
                    self.wikidata_entities.append(res)
                    temp_ids.append(res['item']['value'])

        logging.debug(self.wikidata_entities)

    def add_ids_if_one_entity(self):
        # adds ids if there is only one wikidata entity

        if len(self.wikidata_entities) == 1:
            add_wiki_attr(self, self.wikidata_entities[0])

    def add_ids_if_more_entities(self):

        if len(self.wikidata_entities) > 1:
            winners = compare_entities_and_calculate_score(self)
            if winners[0] == 1: # single winner
                add_wiki_attr(self, self.wikidata_entities[winners[1][0][0]])
            if winners[0] == 0: # no winner
                self.wikidata_entities_to_disambiguate = (0, self.wikidata_entities)
            if winners[0] == 2: # tie
                ent = []
                for e in winners[1]:
                    ent.append(self.wikidata_entities[e[0]])
                self.wikidata_entities_to_disambiguate = (2, ent)

    def get_coords_from_rec(self):
        try:
            self.coordinates = self.full_record.get_fields('034')[0].get_subfields('e', 'f')
        except IndexError:
            pass

    @staticmethod
    def get_geo_auth(catalogue_input_file, limit=None):
        authorities = {}

        with open(catalogue_input_file, 'rb') as fp:
            marc_reader = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')
            i = 1
            prev_id = ''
            for geo_auth in marc_reader:
                if i == limit:
                    break
                try:
                    local_id = normalizacja_ident(geo_auth.get_fields('001')[0].value())
                    prev_id = local_id
                except IndexError:
                    logging.error('Błąd indeksowania. Brak numeru rekordu. Poprzedni numer: {}'.format(prev_id))
                    continue
                if geo_auth.get_fields('151'):
                    try:
                        natural_lang_id = normalizacja_XXX(
                            geo_auth.get_fields('151')[0].get_subfields('a')[0])
                    except IndexError:
                        logging.error('Błąd indeksowania. Brak podpola |a w rekordzie nr: {}'.format(local_id))
                        continue
                    if natural_lang_id not in authorities:  # only headings without subdivisions are selected + dedup
                        authorities[natural_lang_id] = GeoAuthority(local_id, natural_lang_id, geo_auth)
                        i += 1
        return authorities


def reverse_name(name):
    if ', ' in name:
        name = name.split(', ')[1].title() + ' ' + name.split(', ')[0].lower()
    return name


def do_apposition_heuristics(obj):
    # checks for all(?) possible patterns in apposition

    try:
        obj.attribs_nl = obj.nat_lang_id.split(' (')[1][:-1]
        if 'woj.' in obj.attribs_nl:
            obj.woj = re.search(re.compile('woj. [\w,-]*'), obj.attribs_nl).group(0).replace('woj. ', 'Województwo ')
        if 'pow.' in obj.attribs_nl:
            obj.pow = re.search(re.compile('pow. [\w,-]*'), obj.attribs_nl).group(0).replace('pow. ', 'Powiat ')
        if 'gm.' in obj.attribs_nl:
            obj.gm = re.search(re.compile('gm. [\w,-]*'), obj.attribs_nl).group(0).replace('gm. ', 'Gmina ')
        if ';' not in obj.attribs_nl and ',' not in obj.attribs_nl and obj.attribs_nl[0].isupper():
            obj.country_or_settlement = obj.attribs_nl
        if ';' not in obj.attribs_nl and ',' in obj.attribs_nl and obj.attribs_nl[0].isupper():
            obj.country_or_settlement = obj.attribs_nl.split(', ')[0]
            obj.other_admin_units = obj.attribs_nl.split(', ')[1:]
        if ';' in obj.attribs_nl and obj.attribs_nl[0].isupper():
            obj.country_or_settlement, obj.type = obj.attribs_nl.split(' ; ')
        if ';' in obj.attribs_nl and obj.attribs_nl[0].islower():
            try:
                obj.type = obj.attribs_nl.split(' ; ')[1]
            except IndexError:
                pass
            try:
                obj.type = obj.attribs_nl.split(' ; ')[1]
            except IndexError:
                pass
        if obj.attribs_nl[0].islower() and '.' not in obj.attribs_nl:
            obj.type = obj.attribs_nl
    except IndexError as e:
        print(e, obj.nlp_id, obj.natural_lang_id)


def do_short_name_heuristics(obj):
    if 'Gmina' in obj.short_name:
        obj.type = 'Gmina'
        logging.debug('Dodano atrybut na podstawie "do_short_name_heuristics": {}'.format(obj.type))
    if 'Województwo' in obj.short_name:
        obj.type = 'Województwo'
        logging.debug('Dodano atrybut na podstawie "do_short_name_heuristics": {}'.format(obj.type))
    if 'Powiat' in obj.short_name:
        obj.type = 'Powiat'
        logging.debug('Dodano atrybut na podstawie "do_short_name_heuristics": {}'.format(obj.type))


def compare_entities_and_calculate_score(obj):
    # analyses the available metadata and disambiguates entities
    # compares natural language data with Wikidata properties and calculates the score (the more, the better)
    wd_to_dbn_lookup = {'Stolice': ['Q5119'], 'Miasta': ['Q515'], 'Wsie': ['Q3558970', 'Q532'], 'Rzeki': ['Q4022'],
                        'Gminy': ['Q3491915', 'Q15334', 'Q15284', 'Q3504085', 'Q2616791'], 'Powiaty': ['Q247073'],
                        'Części miast': ['Q1434401', 'Q4286337'], 'Obszary chronione': ['Q473972'],
                        'Szczyty górskie': ['Q8502'], 'Dzielnice': ['Q1434401', 'Q4286337'],
                        'Województwa': ['Q150093'], 'Wyspy': ['Q23442'], 'Rezerwaty przyrody': ['Q9309832', 'Q179049'],
                        'Jeziora': ['Q23397'], 'Państwa': ['Q6256']}

    final_scores = []
    for no, entity in enumerate(obj.wikidata_entities):
        score = 0
        try:
            if obj.type:
                if obj.type in entity['instofLabel']['value']:
                    score += 1
            if obj.attribs_368:
                for attribute in obj.attribs_368:
                    for ident in wd_to_dbn_lookup[attribute]:
                        if ident in entity['instof']['value']:
                            score += 1
                            logging.debug("Dodano punkt na podstawie instOfWikidata: {}".format(ident))
                            break
            if obj.gm:
                if obj.gm in entity['adminunitLabel']['value'] or obj.gm[6:] in entity['adminunitLabel']['value']:
                    score += 1
            if obj.pow:
                if obj.pow in entity['adminunitLabel']['value'] or obj.pow[7:] in entity['adminunitLabel']['value']:
                    score += 1
            if obj.woj:
                if obj.woj in entity['adminunitLabel']['value'] or obj.woj[12:] in entity['adminunitLabel']['value']:
                    score += 1
            if obj.country_or_settlement:
                if obj.country_or_settlement in entity['countryLabel']['value']:
                    score += 1
        except Exception as e:
            logging.error(e)
        final_scores.append((no, score))
    final_scores.sort(key=lambda sc_value: sc_value[1], reverse=True)
    logging.debug(final_scores)
    first_score = final_scores[0][1]

    # no result
    if first_score == 0:
        return 0, final_scores

    # score > 0
    if first_score != 0:
        winners = [final_scores[0]]
        print(winners)
        for no, sc in enumerate(final_scores[1:]): # compare scores to each other using loop with offset
            if sc[1] == final_scores[no][1]:
                winners.append(sc)
                print(winners)
            else:
                break
        if len(winners) > 1:
            return 2, winners
        else:
            return 1, winners


def add_wiki_attr(obj, entity):
    obj.wikidata_id = entity['item']['value']
    try:
        obj.geonames_id = entity['geonames']['value']
    except KeyError:
        pass
    try:
        obj.viaf_id = entity['viaf']['value']
    except KeyError:
        pass


def dump_to_csv(fnameout, data):
    with open(fnameout, 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, dialect='excel')
        w.writerows(data.items())


def helper_get_dict_of_prop_368(iterable):
    temp_dict = {}
    for key, it in iterable.items():
        print(key, it)
        if it.attribs_368:
            for attr in it.attribs_368[0]:
                if attr not in temp_dict:
                    temp_dict[attr] = 1
                else:
                    temp_dict[attr] += 1
    dump_to_csv('368-raport.csv', temp_dict)
    return temp_dict


def main_workflow(data):
    for k, v in data.items():
        v.get_attr_from_nat_lang_id()
        v.get_attr_from_368_field()
        v.get_entities_from_wikidata()
        v.add_ids_if_one_entity()
        v.add_ids_if_more_entities()
        print(v.nat_lang_id, v.short_name, v.type, v.country_or_settlement,
              v.woj, v.pow, v.gm, v.other_admin_units, v.wikidata_id, v.geonames_id, v.viaf_id, v.attribs_368)


if __name__ == '__main__':

    logging.root.addHandler(logging.StreamHandler(sys.stdout))
    logging.root.setLevel(level=logging.DEBUG)

    geo_authorities = GeoAuthority.get_geo_auth('authorities-all.marc', limit=500)
    main_workflow(geo_authorities)
