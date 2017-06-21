import requests
from bs4 import BeautifulSoup
import re

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

    for link in links:
        link = 'https://czarne.com.pl' + link.get('href')
        response = requests.get(link).text
        soup = BeautifulSoup(response, 'html.parser')
        isbn = soup.find_all(string=re.compile('83'))
        print(isbn)
        abstract = soup.find_all('div', class_='description')[0]
        abstract = abstract.get_text().replace('\xa0', ' ')
        dict[link] = abstract
        break
    return dict

if __name__ == '__main__':

    start_url = 'https://czarne.com.pl/katalog/ksiazki'
    wynik = scraper_main(start_url)
    print(wynik)
