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

FLAGS = (
    ('Acres',             re.compile(r'((\d+,)*(\d+))\s+acres', re.I),    lambda m: m.group(1) ),
    ('Archery Only',      re.compile(r'archery hunting only', re.I),      lambda m: True ),
    ('Deer Archery Only', re.compile(r'deer archery hunting only', re.I), lambda m: True ),
)

class MDPublicLandsScraper(object):
    def __init__(self):
        self.url = 'http://www.eregulations.com/maryland/hunting/public-hunting-lands/'
        
        FORMAT = "%(asctime)s [ %(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
        logging.basicConfig(format=FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.session = requests.Session()

    def csv_save(self, listings):
        headers = (
            'Name',
            'County',
            'Acres',
            'Archery Only',
            'Deer Archery Only',
            'Free Permit Required',
            'Reservation Required',
            'MHP',
            'Daily Sign-in Required',
        )

        filename = 'public_hunting_lands.csv'
        
        with open(filename, 'w') as fd:
            csvwriter = csv.writer(fd, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow(headers)
            for l in listings:
                row = [ l.get(k) for k in headers ]
                csvwriter.writerow(row)
        
    def xlat_key_codes(self, keys):
        key_code = {
            'f': 'Free Permit Required',
            'r': 'Reservation Required',
            'd': 'Daily Sign-in Required',
            'm': 'MHP',
        }

        d = { key_code[k]: True for k in keys if key_code.get(k) }
        return d

    def get_land_info(self, listing):
        global FLAGS

        h5 = listing.h5
        h2 = h5.find_previous('h2')

        text_list = h5.find_all(text=True)
        name = text_list[0].split(':')[0].strip()
        keys = ''.join(t.strip() for t in text_list[1:])

        e = self.xlat_key_codes(keys)

        e['Name'] = name
        e['County'] = h2.text.strip()
            
        x = {'class': 'Public-Land-Body'}
        p = h5.find_next('p', attrs=x)

        for (k,r,f) in FLAGS:
            m = re.search(r, p.text)
            if m:
                e[k] = f(m)
            
        return e

    def process_sublist(self, listing):
        global FLAGS        
        entries = []

        h5 = listing.h5        
        h2 = h5.find_previous('h2')        
        ul = h5.find_next('ul')

        for li in ul.find_all('li'):
            name = li.strong.text.split(':')[0].strip()
            span = li.select_one('span.Public-Lands-Key-Letters')
            
            if span:
                keys = span.text
            else:
                keys = li.text.split(';')
                if len(keys) > 1:
                    keys = keys[-1].strip()
                else:
                    keys = None

            e = {}
            e['Name'] = name
            e['County'] = h2.text.strip()

            if keys:
                d = self.xlat_key_codes(keys)
                e.update(d)

            for (k,r,f) in FLAGS:
                m = re.search(r, li.text)
                if m:
                    e[k] = f(m)
                
            entries.append(e)

        return entries

    def extract_listing(self, h5):
        h2 = h5.find_previous('h2')

        listing = [ h2, h5 ]
        n = h5.next_sibling
        while True:
            if n == None or n.name in ['h5', 'h2']:
                break
            listing.append(n)
            n = n.next_sibling

        html = ' '.join(str(x) for x in listing)
        soup = BeautifulSoup(html, 'lxml')
        
        return soup

    def scrape(self):
        resp = self.session.get(self.url)
        soup = BeautifulSoup(resp.text, 'lxml')

        lands = []
        
        article = soup.find('article', id=re.compile(r'^post-\d+$'))

        for h5 in article.select('h5'):
            listing = self.extract_listing(h5)

            if listing.find('ul'):
                entries = self.process_sublist(listing)
                lands.extend(entries)
            else:
                e = self.get_land_info(listing)
                lands.append(e)                
                
        return lands

if __name__ == '__main__':
    scraper = MDPublicLandsScraper()
    listings = scraper.scrape()
    print(json.dumps(listings, indent=2))
    scraper.csv_save(listings)
