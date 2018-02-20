from pymarc import *
import logging
import sys


"""
Algorytm importu deskryptorów do bazy danych OMNIS:

wersja: 0.1

wariant A: import z bazy danych Biblioteki Narodowej /wersja wyłącznie dla książek, w których nie ma dzieł współwydanych/

0. ogranicz import do książek, w których nie ma dzieł współwydanych
    0.1 sprawdź, czy rekord jest typu 'Książki'
        0.1.1 jeśli w którymś polu 380 (pole powtarzalne) występuje termin 'Książki' idź do 0.2, jeśli nie pomiń rekord
    0.2 wyklucz rekordy skomplikowane i zawierające dzieła współwydane
        0.2.1 jeśli w rekordzie występuje którekolwiek z poniższych pól|podpól, pomiń rekord, jeśli nie idź do 1A
            130
            730
            240
            740
            700 i występuje podpole |t
            710 i występuje podpole |t
            711 i występuje podpole |t

1A. sprawdź, czy rekord materializacji jest już w bazie OMNIS
    sprawdź po identyfikatorze BN (mNlpId)
    jeśli jest w bazie, zaktualizuj encje związane z rekordem (idź do 2 i 3B)
    jeśli brak, sprawdź czy w bazie są związane z nim encje (dzieło lub realizacja) (idź do 1B)

1B. sprawdź, czy w bazie są związane z rekordem materializacji encje (dzieło lub realizacja)
    1B.0 [opcjonalnie] dokonaj wstępnej dekompozycji rekordu, aby pobrać metadane potrzebne do matchowania
    1B.1 sprawdź, czy w bazie jest już dane dzieło
        1B.1.1 sprawdź, czy w bazie jest już dzieło pod danym tytułem oryginału
         (246|a|b jeśli  vs. wspólny indeks tytułów)
        1B1.2 sprawdź, czy w bazie jest już dzieło
        
    
2. 

1. sprawdź typ rekordu (czy w rekordzie obecne konkretne pole 1XX?)
    100 i brak podpola |t - deskryptor osobowy
    110 i brak podpola |t - deskryptor korporatywny
    111 i brak podpola |t - deskryptor imprezy
    150 - deskryptor przedmiotowy
    151 - deskryptor geograficzny
    155 - deskryptor formy/rodzaju/gatunku
2. wyklucz hasła przedmiotowe rozwinięte
    jeśli w polu 1XX występuje |x lub |y lub |z pomiń rekord
3. sprawdź, czy rekord jest już w bazie
    sprawdź po identyfikatorze BN (descrNlpId)
    jeśli jest w bazie, zaktualizuj rekord (idź do 3 i 4B)
    jeśli brak, utwórz rekord (idź do 3 i 4A)
3. skonwertuj rekord
4A. dodaj rekord do bazy danych
4B. zaktualizuj rekord
"""

class BookSingle(object):
    def __init__(self, nr_bn, title_245, author_100):
        self.nr_bn = nr_bn
        self.title_245 = title_245
        self.author_100 = author_100

    @staticmethod
    def importuj_book_single(baza_bn, limit=None):
        to_check = [('130', None), ('730', None), ('240', None), ('740', None), ('700', 't'), ('710', 't'),
                    ('711', 't')]
        records = {}

        with open(baza_bn, 'rb') as fp:
            marc_reader = MARCReader(fp, to_unicode=True, force_utf8=True, utf8_handling='ignore')
            i = 1

            for book_record in marc_reader:
                if i == limit:
                    break
                nlp_id = book_record.get_fields('001')[0].value()  # pobiera numer rekordu
                record_type = [v.value() for v in book_record.get_fields('380')]  # pobiera typ rekordu

                if 'Książki' in record_type:  # sprawdza, czy rekord jest typu książka
                    logging.debug('Rekord {} zawiera pole {} i jest typu {}.'.format(nlp_id, '380', 'Książki'))
                    score = 0
                    for marc_field, marc_subfield in to_check:  # sprawdza, czy rekord nie zawiera niedozwolonych (pod)pól
                        if marc_subfield:
                            for fld in book_record.get_fields(marc_field):
                                if fld.get_subfields(marc_subfield):
                                    logging.debug('Rekord {} zawiera pole {}|{}.'.format(nlp_id, marc_field, marc_subfield))
                                    break
                        else:
                            if book_record.get_fields(marc_field):
                                logging.debug('Rekord {} zawiera pole {}. Pomijam.'.format(nlp_id, marc_field))
                                break
                        score += 1

                    if score == 7:  # rekord nadaje się do importu, można go dalej przetwarzać
                        title_245 = book_record.get_fields('245')[0].value()
                        if book_record.get_fields('100'):
                            author_100 = book_record.get_fields('100')[0].value()
                        records[nlp_id] = BookSingle(nlp_id, title_245, author_100)
                        logging.debug('Ok. Rekord nie zawiera niedozwolonych (pod)pól. Dodaję rekord {}. [{}]'.format(nlp_id, i))
                        i += 1
        return records


class Work(object):
    # wrapper around full MARC record
    def __init__(self, book_single):
        self.nr_bn = book_single.nr_bn
        self.title_pref = book_single.nat_lang_id
        self.title_orig = full_record


if __name__ == '__main__':

    logging.root.addHandler(logging.StreamHandler(sys.stdout))
    logging.root.setLevel(level=logging.DEBUG)

    books = BookSingle.importuj_book_single('bibs-ksiazka.marc', limit=38000)
    for nrbn, book in books.items():
        print(nrbn, book.title_245, book.author_100)

    books_by_title = {}
    for book in books.values():
        books_by_title[book.title_245] = book
    for title, book in books_by_title.items():
        print(title, book.title_245, book.author_100)
