import os
from re import sub, findall
from collections import defaultdict
from wiktionaryparser import WiktionaryParser
from bs4 import BeautifulSoup
import sqlite3
import requests

wp = WiktionaryParser()

class Thesaurus:

    # the order that the results will be shown in string output
    results_order = 'synonyms', 'antonyms'
    # assigns indices to filters in the header in string output
    filter_order = ('AWL', 0),
    # symbols used in string output to indicate which word lists word is in
    symbols = {
        'found': 'X',
        'not_found': ''
    }

    db_path='wordnet.db'

    def __init__(self, *filters, filter_dir='filters', required=None):
        if type(required) is str:
            required = [required.lower()]
        elif type(required) in [tuple, list]:
            required = [r.lower() for r in required]
        self.required = required

        filter_dir = 'filters'
        filter_files = os.listdir(filter_dir)

        if filters:
            filter_files = [f for f in filter_files if [filter for filter in filters if f.startswith(filter)]]

        self.filters = {}

        for ff in filter_files:
            with open(os.path.join(filter_dir, ff)) as f:
                self.filters[ff.split('.txt')[0]] = f.read().splitlines()

        self.set_getters()

    def set_getters(self):
        self.getters =  self.get_wiktionary, self.get_db


    def get(self, word):
        results = defaultdict(list)
        for getter in self.getters:
            matches = getter(word)
            for key in matches:
                results[key] += matches[key]

        results = {key: list(sorted(set(results[key]))) for key in results}
        output = {key: [] for key in results}

        for key in results:
            for item in results[key]:
                found_in = self.in_filter(item)
                if self.required is None or (found_in and self.required is not None):
                    output[key] += [[item, found_in]]

        return output

    def get_as_string(self, word, *categories):
        if not categories:
            categories = self.results_order[:]

        results = self.get(word)

        # figures out max length of the item in the first column in order to justify with whitespace later
        first_col_items = []

        for key in results:
            for item in results[key]:
                first_col_items.append(item[0])

        if not first_col_items:
            return 'No matches found for {}.'.format(word)

        first_col_items += categories
        first_col_len = len(max(first_col_items, key=len))

        filter_names = sorted(f for f in self.filters)

        for fn_i, fn in enumerate(filter_names):
            for f, f_i in self.filter_order:
                if fn.lower() == f.lower():
                    filter_names.insert(f_i, filter_names.pop(fn_i))
        output = []

        for category in [c for c in categories if results[c]]:
            header = [category.upper().ljust(first_col_len)] + filter_names
            output.append(header)

            for item, found_in in results[category]:
                row = [item.ljust(first_col_len)]

                for fn in filter_names:
                    if fn in found_in:
                        row.append(self.symbols['found'].center(len(fn)))
                    else:
                        row.append(self.symbols['not_found'].center(len(fn)))

                output.append(row)
            output.append([] * len(output[-1]))

        return '\n'.join('\t'.join(row) for row in output)

    def in_filter(self, word):
        output = []
        for key in self.filters:
            if word in self.filters[key]:
                    output.append(key)
            elif self.required is not None and key.lower() in self.required:
                return []
        return output


    def get_db(self, word):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        results = c.execute("""SELECT * FROM words WHERE word = '{}' """.format(word.lower()))
        results = list(results)
        if results:
            results = results[0]
            synonyms = results[1].split('\t') if results[1] else []
            antonyms = results[2].split('\t') if results[2] else []
        else:
            synonyms, antonyms = [], []
        return {
            'synonyms': synonyms,
            'antonyms': antonyms
        }

    def clean_wiktionary(self, words):
        words = sub('\(.*?\):', '', words)
        words = sub(';\ssee\salso.*|See\salso.*', '', words)
        words = words.replace(';', '')
        words = words.strip()
        words = words.split(', ')
        return words

    def get_wiktionary(self, word, language='English'):
        entries = wp.fetch(word, language)
        synonyms, antonyms = [], []

        for entry in entries:
            for definition in entry['definitions']:
                for relationship in definition['relatedWords']:
                    if relationship['relationshipType'] == 'synonyms':
                        for words in relationship['words']:
                            synonyms += self.clean_wiktionary(words)
                            if 'see also thesaurus:' in words.lower():
                                thesaurus_title = words.lower().split('thesaurus:')[-1].strip()
                                thesaurus_words = self.get_wiktionary_thesaurus(thesaurus_title)
                                more_words = self.get_wiktionary_thesaurus(thesaurus_title, 'synonyms', 'antonyms')
                                synonyms += more_words['synonyms']
                                antonyms += more_words['antonyms']
                    elif relationship['relationshipType'] == 'antonyms':
                        for words in relationship['words']:
                            antonyms += self.clean_wiktionary(words)

        return {
            'synonyms': set(synonyms),
            'antonyms': set(antonyms)
        }

    def get_wiktionary_thesaurus(self, word, *categories):
        word = word.replace(' ', '_')
        url = 'https://en.wiktionary.org/w/index.php?title=Thesaurus:{}&printable=yes'.format(word)

        categories = [c.lower() for c in categories]
        output = {}

        session = requests.Session()
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=2))
        response = session.get(url)

        soup = BeautifulSoup(response.text, 'html.parser')
        content = soup.find('div', attrs={'id': 'mw-content-text'})
        if content:
            content = content.__repr__().replace('\n', '')
            content = findall('(<h5>.*?</div>)', content)
            for section in content:
                soup = BeautifulSoup(section, 'html.parser')
                span = soup.find('span')
                if span and soup.span.text.lower() in categories:
                    key = soup.span.text.lower()
                    links = soup.find_all('a')
                    if links:
                        words = [a.text.replace('_', ' ') for a in links
                                 if a.get('href', '').startswith('/wiki/') and not
                                 a.get('href', '').startswith('/wiki/Thesaurus:')]
                        output[key] = words

        return output


