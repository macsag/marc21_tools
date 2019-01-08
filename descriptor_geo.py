import logging
import sys
import re
import csv

from pymarc import MARCReader
from marc_tools import normalizacja_XXX
from marc_tools import normalizacja_ident
from SPARQLWrapper import SPARQLWrapper, JSON


class GeographicalDescriptor(object):
    # wrapper for full MARC record

    def __init__(self, nr_bn, nat_lang_id, full_record):
        self.nr_bn = nr_bn # sierra id
        self.nat_lang_id = nat_lang_id # 151 field: descr_name (record heading)
        self.full_record = full_record # full parsed record (pymarc.record.Record)

        self.viaf_id = None
        self.wikidata_id = None
        self.geonames_id = None

        self.type = None # type of administrative unit parsed from short_name (gmina, powiat, województwo)
        self.coordinates = None # 034 field: descr_geometrya, descr_geometryb; currently not used for disambiguation
        self.short_name = None # 151 field without apposition, reversed if applicable (Arabskie, kraje - Kraje arabskie)
        self.apposition = None

        self.country_or_settlement = None
        self.woj = None # województwo parsed from apposition
        self.pow = None # powiat parsed from apposition
        self.gm = None # gmina parsed from apposition
        self.other_admin_units = None # other administrative units parsed from apposition

        self.attributes_368 = None # 368 field: descr_type (Parki krajobrazowe, Obszary chronione, etc.); used for disambiguation

        self.wikidata_entities = []
        self.wikidata_entities_to_disambiguate = None

    @staticmethod
    def get_geographical_descriptors(catalogue_input_file, limit=None):
        # reads descriptors from marc iso (transmission) format and instantiates GeographicalDescriptor objects
        # returns dict with natural_lang_id (151 field) as a key and GeographicalDescriptor object as a value

        descriptors = {}

        with open(catalogue_input_file, 'rb') as fp:
            marc_reader = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')
            i = 1
            prev_id = '' # if pymarc.exceptions.NoFieldsFound is raised, you know where to look for invalid record
            for geo_descriptor in marc_reader:
                if i == limit:
                    break
                try:
                    local_id = normalizacja_ident(geo_descriptor.get_fields('001')[0].value())
                    prev_id = local_id
                except IndexError:
                    logging.error('Błąd indeksowania. Brak numeru rekordu. Poprzedni numer: {}'.format(prev_id))
                    continue
                if geo_descriptor.get_fields('151'):
                    try:
                        natural_lang_id = normalizacja_XXX(
                            geo_descriptor.get_fields('151')[0].get_subfields('a')[0])
                    except IndexError:
                        logging.error('Błąd indeksowania. Brak podpola |a w rekordzie nr: {}'.format(local_id))
                        continue
                    if natural_lang_id not in descriptors:  # only headings without subdivisions are selected + dedup
                        descriptors[natural_lang_id] = GeographicalDescriptor(local_id, natural_lang_id, geo_descriptor)
                        i += 1
        return descriptors

    def get_short_name_and_appossition(self):
        # splits 151 field (heading) into short name and apposition (if applicable)

        if ' (' in self.nat_lang_id:  # checks if apposition exists
            self.short_name = reverse_name(self.nat_lang_id.split(' (')[0]) # sets short name (truncates apposition)
            self.apposition = self.nat_lang_id.split(' (')[1][:-1] # sets apposition (truncates brace at the end)
        else:
            self.short_name = reverse_name(self.nat_lang_id) # sets short name if there is no apposition

    def get_attributes_from_368_field(self):
        try:
            # there can be more than one subfield b in 368 field; get_subfields returns a list
            self.attributes_368 = self.full_record.get_fields('368')[0].get_subfields('b')
        except IndexError:
            pass

    def get_coords_from_rec(self):
        try:
            self.coordinates = self.full_record.get_fields('034')[0].get_subfields('e', 'f')
        except IndexError:
            pass

    def do_apposition_heuristics(self):
        # checks for all(?) possible patterns in apposition
        if self.apposition:
            try:
                if 'woj.' in self.apposition:
                    self.woj = re.search(re.compile('woj. [\w,-]*'), self.apposition).group(0).replace('woj. ',
                                                                                                       'Województwo ')
                if 'pow.' in self.apposition:
                    self.pow = re.search(re.compile('pow. [\w,-]*'), self.apposition).group(0).replace('pow. ', 'Powiat ')
                if 'gm.' in self.apposition:
                    self.gm = re.search(re.compile('gm. [\w,-]*'), self.apposition).group(0).replace('gm. ', 'Gmina ')
                if ';' not in self.apposition and ',' not in self.apposition and self.apposition[0].isupper():
                    self.country_or_settlement = self.apposition
                if ';' not in self.apposition and ',' in self.apposition and self.apposition[0].isupper():
                    self.country_or_settlement = self.apposition.split(', ')[0]
                    self.other_admin_units = self.apposition.split(', ')[1:]
                if ';' in self.apposition and self.apposition[0].isupper():
                    self.country_or_settlement, self.type = self.apposition.split(' ; ')
                if ';' in self.apposition and self.apposition[0].islower():
                    try:
                        self.type = self.apposition.split(' ; ')[1]
                    except IndexError:
                        pass
                if self.apposition[0].islower() and '.' not in self.apposition:
                    self.type = self.apposition
            except IndexError as e:
                logging.error('{} - {} - {}'.format(e, self.nr_bn, self.nat_lang_id))

    def do_short_name_heuristics(self):
        # short name may contain some useful information about type of administrative unit or geographical unit
        # unfortunately, they don't have to be explicitly coded in other marc fields (but sometimes they are)
        # this section can be expanded

        if 'Gmina' in self.short_name:
            self.type = 'Gmina'
            logging.debug('Dodano atrybut na podstawie "do_short_name_heuristics": {}'.format(self.type))
        if 'Województwo' in self.short_name:
            self.type = 'Województwo'
            logging.debug('Dodano atrybut na podstawie "do_short_name_heuristics": {}'.format(self.type))
        if 'Powiat' in self.short_name:
            self.type = 'Powiat'
            logging.debug('Dodano atrybut na podstawie "do_short_name_heuristics": {}'.format(self.type))


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
                }""")

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
            self.add_wiki_attr(0)

    def add_ids_if_more_entities(self):

        if len(self.wikidata_entities) > 1:
            winners = self.compare_entities_and_calculate_score()
            if winners[0] == 1: # single winner
                self.add_wiki_attr(winners[1][0][0])
            if winners[0] == 0: # no winner
                self.wikidata_entities_to_disambiguate = (0, self.wikidata_entities)
            if winners[0] == 2: # tie
                entities = []
                for entity in winners[1]:
                    entities.append(self.wikidata_entities[entity[0]])
                self.wikidata_entities_to_disambiguate = (2, entities)

    def compare_entities_and_calculate_score(self):
        # analyses the available metadata and disambiguates entities
        # compares natural language data with Wikidata properties and calculates the score (the more, the better)
        wd_to_dbn_lookup = {'Stolice': ['Q5119'], 'Miasta': ['Q515'], 'Wsie': ['Q3558970', 'Q532'], 'Rzeki': ['Q4022'],
                            'Gminy': ['Q3491915', 'Q15334', 'Q15284', 'Q3504085', 'Q2616791'], 'Powiaty': ['Q247073'],
                            'Części miast': ['Q1434401', 'Q4286337'], 'Obszary chronione': ['Q473972'],
                            'Szczyty górskie': ['Q8502'], 'Dzielnice': ['Q1434401', 'Q4286337'],
                            'Województwa': ['Q150093'], 'Wyspy': ['Q23442'],
                            'Rezerwaty przyrody': ['Q9309832', 'Q179049'],
                            'Jeziora': ['Q23397'], 'Państwa': ['Q6256']}

        final_scores = []
        for no, entity in enumerate(self.wikidata_entities):
            score = 0

            try:
                if self.type:
                    if self.type in entity['instofLabel']['value']:
                        score += 1
                        logging.debug(
                            "Dodano punkt na podstawie typu jednostki instOfLabel, nazwa naturalna: {}".format(self.type))
                if self.attributes_368:
                    for attribute in self.attributes_368:
                        for ident in wd_to_dbn_lookup[attribute]:
                            if ident in entity['instof']['value']:
                                score += 1
                                logging.debug(
                                    "Dodano punkt na podstawie typu jednostki instOfWikidata, id encji: {}".format(ident))
                                break
                if self.gm:
                    if self.gm in entity['adminunitLabel']['value'] or self.gm[6:] in entity['adminunitLabel']['value']:
                        score += 1
                        logging.debug(
                            "Dodano punkt na podstawie nazwy gminy: {}".format(self.gm))
                if self.pow:
                    if self.pow in entity['adminunitLabel']['value'] or self.pow[7:] in entity['adminunitLabel'][
                        'value']:
                        score += 1
                        logging.debug(
                            "Dodano punkt na podstawie nazwy powiatu: {}".format(self.pow))
                if self.woj:
                    if self.woj in entity['adminunitLabel']['value'] or self.woj[12:] in entity['adminunitLabel'][
                        'value']:
                        score += 1
                        logging.debug(
                            "Dodano punkt na podstawie nazwy województwa: {}".format(self.woj))
                if self.country_or_settlement:
                    if self.country_or_settlement in entity['countryLabel']['value']:
                        score += 1
                        logging.debug(
                            "Dodano punkt na podstawie nazwy kraju: {}".format(self.country_or_settlement))
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

            # compare scores to each other using loop with offset
            # it definitely can be done in a smarter and more readable way
            for no, sc in enumerate(final_scores[1:]):
                if sc[1] == final_scores[no][1]:
                    winners.append(sc)
                    print(winners)
                else:
                    break
            if len(winners) > 1:
                return 2, winners
            else:
                return 1, winners

    def add_wiki_attr(self, index):
        self.wikidata_id = self.wikidata_entities[index]['item']['value']
        try:
            self.geonames_id = self.wikidata_entities[index]['geonames']['value']
        except KeyError:
            pass
        try:
            self.viaf_id = self.wikidata_entities[index]['viaf']['value']
        except KeyError:
            pass


def reverse_name(name):
    if ', ' in name:
        name = name.split(', ')[1].title() + ' ' + name.split(', ')[0].lower()
    return name

def helper_dump_to_csv(fnameout, data):
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
    helper_dump_to_csv('368-raport.csv', temp_dict)
    return temp_dict


def main_workflow(data):
    # returns tuple with 3 dicts containing GeographicalDescriptor objects; keys are descriptors names (headings)
    # 1st dict: enriched descriptors (disambiguation not needed)
    # 2nd dict: descriptors to disambiguate (2 candidates)
    # 3rd dict: descriptors to disambiguate (more than 2 candidates)

    result = {}
    tie_2 = {}
    tie_more_than_2 = {}

    # main loop starts here
    for k, v in data.items():
        v.get_short_name_and_appossition()
        v.do_short_name_heuristics()
        v.do_apposition_heuristics()
        v.get_attributes_from_368_field()
        v.get_entities_from_wikidata()
        v.add_ids_if_one_entity()
        v.add_ids_if_more_entities()

        output_preview = [v.nat_lang_id, v.short_name, v.type, v.country_or_settlement,
              v.woj, v.pow, v.gm, v.other_admin_units, v.wikidata_id, v.geonames_id, v.viaf_id, v.attributes_368]
        logging.debug(output_preview)

        if v.wikidata_id:
            result[k] = v

        if v.wikidata_entities_to_disambiguate:
            if len(v.wikidata_entities_to_disambiguate) == 2:
                tie_2[k] = v
            else:
                tie_more_than_2[k] = v

    return result, tie_2, tie_more_than_2



if __name__ == '__main__':


    logging.root.addHandler(logging.StreamHandler(sys.stdout))
    logging.root.setLevel(level=logging.DEBUG)

    geo_authorities = GeographicalDescriptor.get_geographical_descriptors('authorities-all.marc', limit=100)
    enriched_auth = main_workflow(geo_authorities)
    print(len(enriched_auth[0]))
    print(len(enriched_auth[1]))
    print(len(enriched_auth[2]))
