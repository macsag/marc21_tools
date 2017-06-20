#!/usr/bin/python3

import logging
import sys

import requests
from urllib.parse import urljoin

from lxml import html
import json

from datetime import datetime, date


class Streszczenie(object):
    __slots__ = ['name', 'start_date', 'end_date', 'url']

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, kwargs[k])

    @staticmethod
    def from_json(fp):
        return Battle(**json.load(fp))

    def to_json(self):
        return json.dumps(dict((k, getattr(self, k)) for k in self.__slots__))


class BattleScraper(object):
    def __init__(self):
        self.logger = logging.getLogger(BattleScraper.__name__)
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.setLevel(level=logging.ERROR)
        # self.logger.setLevel(level=logging.DEBUG)
        self.session = requests.Session()
        self.home_url = None

    def _parse_date(self, date_str):
        date_format = '%d %B %Y'  # https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior

        def parse_start_date(start_date_str, end_date):
            try:
                return datetime.strptime(start_date_str, date_format)
            except ValueError:
                pass

            try:
                # let's try some heuristics :)
                start_date_with_year = '{0} {1:%Y}'.format(start_date_str, end_date)
                return datetime.strptime(start_date_with_year, date_format)
            except ValueError:
                pass

            try:
                start_date_with_month_and_year = '{0} {1:%B} {1:%Y}'.format(start_date_str, end_date)
                return datetime.strptime(start_date_with_month_and_year, date_format)
            except ValueError:
                pass

            self.logger.error('Cannot understand date string: %s', start_date_str)
            return None

        date_list = date_str.split('–')
        if len(date_list) > 2:
            self.logger.error('Cannot understand date string: %s', date_str)
            return None, None

        try:
            end_date = datetime.strptime(date_list[-1].strip(), date_format)
        except ValueError:
            self.logger.error('Cannot understand date string: %s', date_list[-1])
            return None, None

        if len(date_list) == 1:
            start_date = end_date
        else:
            start_date = parse_start_date(date_list[0].strip(), end_date)

        return (date.isoformat(start_date.date()) if start_date else None,
                date.isoformat(end_date.date()) if end_date else None)

    def get_battles(self, u):
        self.home_url = u
        response = self.session.get(u)
        tree = html.fromstring(response.content)
        for elt in tree.xpath('//*[@id="mw-content-text"]/ul/li'):
            a_list = elt.xpath('./a')
            if len(a_list) == 0:
                self.logger.error('Cannot get link: %s', ''.join(elt.xpath('.//text()')))
                continue
            a = a_list[0]
            date_str = ''.join(elt.xpath('./text()'))
            start_date, end_date = self._parse_date(date_str)
            if not start_date or not end_date:
                continue

            url = urljoin(self.home_url, a.get('href'))
            yield Battle(name=a.text, url=url, start_date=start_date, end_date=end_date)


def scrape_all(output_file):
    bs = BattleScraper()
    home_url = 'https://en.wikipedia.org/wiki/List_of_Napoleonic_battles'
    for i, b in enumerate(bs.get_battles(home_url)):
        bs.logger.debug('%d : %s', i, b.name)
        bs.logger.debug('  start date: %s', b.start_date)
        bs.logger.debug('  end date: %s', b.end_date)
        bs.logger.debug('  url: %s', b.url)
        with open(output_file, 'a') as fp:
            fp.write(b.to_json() + '\n')

def parse(output_file):
    battle_list = []
    with open(output_file) as fp:
        for line in fp:
            elt = json.loads(line)
            battle_list.append(Battle(**elt))

    battle_list.sort(key=lambda b: b.end_date)
    print(battle_list[0].url)


if __name__ == '__main__':
    output_file = 'battles.json'
    scrape_all(output_file)
    parse(output_file)


książki mają klasę product-item
