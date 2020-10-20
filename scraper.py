import re
import csv
import sys
import time
import json
import logging
import argparse
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin

RE_ACRES = re.compile(r'((\d+,)*(\d+))\s+acres')
RE_ARCHERY_ONLY = re.compile(r'archery hunting only')

class MDPublicLandsScraper(object):
    def __init__(self):
        self.url = 'http://www.eregulations.com/maryland/hunting/public-hunting-lands/'
        
        FORMAT = "%(asctime)s [ %(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
        logging.basicConfig(format=FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.session = requests.Session()

    def csv_save(self, lands):
        headers = {
            'Name',
            'Archery Only',
            'Free Permit Required',
            'Reservation Required',
            'MHP',
            'Daily Sign-in Required',
        }

    def xlat_key_codes(self, keys):
        key_code = {
            'f': 'Free Permit Required',
            'r': 'Reservation Required',
            'd': 'Daily Sign-In Required',
            'm': 'MHP',
        }

        d = { key_code[k]: True for k in keys if key_code.get(k) }
        return d

    def get_land_info(self, h5):
        global RE_ACRES, RE_ARCHERY_ONLY
        
        h2 = h5.find_previous('h2')

        text = h5.text.split(':')
        name = text[0]
        keys = text[1]

        e = self.xlat_key_codes(keys)

        e['name'] = name
        e['county'] = h2.text.strip()
            
        x = {'class': 'Public-Land-Body'}
        p = h5.find_next('p', attrs=x)
            
        m = re.search(RE_ACRES, p.text)
        if m:
            e['acres'] = m.group(1)

        m = re.search(RE_ARCHERY_ONLY, p.text)
        if m:
            e['archery_only'] = True

        return e

    def process_sublist(self, h5):
        entries = []

        h2 = h5.find_previous('h2')        
        ul = h5.find_next('ul')

        for li in ul.find_all('li'):
            text = li.text.split(':')
            name = text[0]
            desc = text[1]
            keys = desc.split(';')

            e = {}
            e['name'] = name
            e['county'] = h2.text.strip()
            
            if len(keys) > 1:
                d = self.xlat_key_codes(keys[-1].strip())
                e.update(d)

            entries.append(e)

        return entries

    def scrape(self):
        resp = self.session.get(self.url)
        soup = BeautifulSoup(resp.text, 'lxml')

        lands = []
        
        article = soup.find('article', id=re.compile(r'^post-\d+$'))

        for h5 in article.select('h5'):
            if h5.text.find(':') != -1:
                e = self.get_land_info(h5)
                lands.append(e)                
            else:
                entries = self.process_sublist(h5)
                lands.extend(entries)
                
        return lands

if __name__ == '__main__':
    scraper = MDPublicLandsScraper()
    scraper.scrape()
