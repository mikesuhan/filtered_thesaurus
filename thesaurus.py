import os
from re import sub
from collections import defaultdict
from nltk.corpus import wordnet as wn
from wiktionaryparser import WiktionaryParser

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
        self.getters = self.get_wordnet, self.get_wiktionary


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
                if found_in:
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

    def check_lemmas(self, lemma):
        for lemma_name in lemma.synset().lemma_names():
            lemma_name = ' '.join(lemma_name.split('_'))
            yield lemma_name

    def clean_wiktionary(self, words):
        words = sub('\(.*?\):', '', words)
        words = sub(';\ssee\salso.*', '', words)
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
                    elif relationship['relationshipType'] == 'antonyms':
                        for words in relationship['words']:
                            antonyms += self.clean_wiktionary(words)

        return {
            'synonyms': set(synonyms),
            'antonyms': set(antonyms)
        }



    def get_wordnet(self, word):
        synonyms, antonyms = [], []

        for synset in wn.synsets(word):
            for lemma in synset.lemmas():
                for match in self.check_lemmas(lemma):
                    if match not in synonyms:
                        synonyms.append(match)

                # adds antonyms
                for antonym_lemma in lemma.antonyms():
                    for match in self.check_lemmas(antonym_lemma):
                        if match not in antonyms:
                            antonyms.append(match)


        return {
            'synonyms': set(synonyms),
            'antonyms': set(antonyms)
        }

