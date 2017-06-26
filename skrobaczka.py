import requests
from bs4 import BeautifulSoup
import re
import time
import csv


def get_start_page(url):
    response = requests.get(url)
    print(response.status_code)
    return response.text

def scraper_url(start_url):
    soup = BeautifulSoup(get_start_page(start_url), 'html.parser')
    links = soup.find_all('a', class_='product product-item book')
    return links

def scraper_main(start_url):
    links = scraper_url(start_url)
    dict = {}
    count = 0
    for link in links:
        if count < 30:
            link = 'https://czarne.com.pl' + link.get('href')
            response = requests.get(link).text
            print('Getting: ' + link)
            soup = BeautifulSoup(response, 'html.parser')
            try:
                isbn = soup.find_all(string=re.compile('83'))[0]
            except IndexError as e:
                print('Książka nie ma isbnu: ' + link)
                continue
            isbn = normalize_isbn(isbn)
            abstract = soup.find_all('div', class_='description')[0]
            abstract = abstract.get_text().replace('\xa0', ' ').replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
            print(abstract)
            if abstract.startswith('Przekład'):
                count2 = 0
                c_prev = ''
                c_prev_prev = ''
                for c in abstract:
                    if c.isupper() and c_prev.islower():
                        break
                    elif c.isupper() and c_prev.isspace() and c_prev_prev.islower:
                        break
                    else:
                        if count == 0:
                            count2 += 1
                            c_prev = c
                        else:
                            count2 += 1
                            c_prev = c
                            c_prev_prev = c_prev
                dict[isbn] = [link, abstract[count2:]]
            else:
                dict[isbn] = [link, abstract]
            print(abstract[count2:])
            time.sleep(1)
            count += 1
        else:
            break
    return dict

def normalize_isbn(isbn):
    isbn = isbn.replace('-', '')
    return isbn

def get_marc_records(dict_isbn):
    not_in_library = {}
    marc_in_json = {}
    for key, value in dict_isbn.items():
        r = requests.get('http://data.bn.org.pl/api/bibs.json?isbnIssn={isbn}'.format(isbn=key))
        r = r.json()
        if not r['bibs']:
            not_in_library[key] = value[0]
        else:
            marc_in_json[r['bibs'][0]['marc']['fields'][0]['001']] = [r['bibs'][0]['title'], value[0], value[1]]
    do_csv('streszczenia.csv', marc_in_json)
    do_csv('braki_w_bn.csv', not_in_library)
    return marc_in_json, not_in_library

def do_csv(fnameout, raport):
    with open(fnameout, 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp)
        w.writerows(raport.items())

if __name__ == '__main__':

    start_url = 'https://czarne.com.pl/katalog/ksiazki'
    wynik = scraper_main(start_url)
    print(get_marc_records(wynik))
