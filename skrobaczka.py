import requests
from bs4 import BeautifulSoup

def get_start_page(url):
    response = requests.get(url)
    print(response.status_code)
    return response.text

def scraper_url(start_url):
    soup = BeautifulSoup(get_start_page(url), 'html.parser')
    links = (soup.find_all('a', class_='product product-item book'))
    return links

def scraper_main(start_url):
    links = scraper_url(start_url)
    dict = {}

    for link in links:
        link = 'https://czarne.com.pl' + link.get('href')
        soup = BeautifulSoup(link, 'html.parser')





if __name__ == '__main__':

    start_url = 'https://czarne.com.pl/katalog/ksiazki'
    scraper_main(start_url)