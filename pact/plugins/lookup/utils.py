"""Monolingual definitions and examples from thefreedictionary.es

Doesn't include <strong> entries.  See
comments for details.
"""

from bs4 import BeautifulSoup as bs
import re
from requests import get
import sys

# section data-src="Larousse_GDLE"

class TheFreeDictionary:
    """Base class for lookups for monolingual definitions and examples.

    Different languages have different .thefreedictionary.com domains, e.g.:

    Spanish: https://es.thefreedictionary.com
    German: https://de.thefreedictionary.com
    French: https://fr.thefreedictionary.com

    These pages appear to differ in a few ways, but their underlying
    structure is approximately equal.
    """

    def __init__(
            self,
            url,
            include_section_data_src = [],
            root_tag = 'h2',
            exclude = [],
            include = [ 'div.ds-single', 'div.ds-list' ],
            ):

        self.url = url
        self.include_section_data_src = include_section_data_src
        self.root_tag = root_tag
        self.exclude = exclude
        self.include = include


    def __extract_definition_and_illustration(self, soup):

        illustrations = [
            s.text
            for s in
            soup.select('span.illustration')
        ]
        # print(illustrations)

        def _get_span_class(c, prechar = ''):
            ret = ''
            spans = soup.select(f'span.{c}')
            if len(spans) > 0:
                ret = f' ({prechar}{spans[0].text.strip()})'
            return ret

        syn = _get_span_class('Syn', '')
        ant = _get_span_class('Ant', '! ')

        # Remove cruft, will use the rest for the definition itself.
        for c in ('illustration', 'Syn', 'Ant'):
            for s in soup.find_all('span', {'class': c}):
                s.decompose()

        # Extra terms are sometimes included as italicized text at the
        # start of the definition.
        # definition = definition.replace('<i>', '[')
        # definition = definition.replace('</i>', ']')
        for node in soup.find_all('i'):
            node.replace_with(f'[{node.text}]')

        # Remove numbering from the text.
        definition = re.sub('^\d+\. ', '', soup.text)
        return {
            'definition': f'{definition.strip()}{syn}{ant}',
            'example': '; '.join(illustrations).strip()
        }


    def get_soup(self, word):
        query_url = f"{self.url}/{word}"
        raw = get(query_url).content.decode('utf-8')

        # During dev, save to and then read from a file,
        # saves time.
        # with open('dumpfile.html', 'w') as f:
        #   f.write(raw)
        # with open('dumpfile.html', 'r') as f:
        #   raw = f.read()
        # print(raw)

        soup = bs(raw, features='html.parser')
        return soup


    def __parse_soup(self, soup):

        # print(soup)
        # print(f'parse section {section}')
        for e in self.exclude:
            tag, klass = e.split('.')
            # print(f'REMOVING: tag = {tag}, class = {klass}')
            toremove = soup.find_all(tag, class_ = klass)
            # print(f'count of things to remove: {len(toremove)}')
            for s in toremove:
                # print(s)
                s.decompose()

        sections = [
            soup.find('section', attrs={ 'data-src' : data_src })
            for data_src
            in self.include_section_data_src ]
        if len(sections) == 0:
            print('no sections')
            return None
        if sections[0] is None:
            print('empty first section')
            return None

        # Simplification: use the first section for the root.
        rootnode = sections[0].find_all(self.root_tag)
        if len(rootnode) == 0:
            print('no root')
            return None
        root = rootnode[0].text.strip()

        definitions = []
        for section in sections:
            for c in self.include:
                # print(f'loading {c}')
                definitions += section.select(c)

        definitions = [
            self.__extract_definition_and_illustration(d)
            for d in definitions

            # FreeDict returns some entries as <strong> entries.  E.g.,
            # searching for "perro" returns a number of different dog types,
            # sayings, etc.  Assuming for now that I'm only looking for
            # general entries.
            if len(d.select('strong')) == 0
        ]

        return {
            'root': root,
            'definitions': definitions
        }


    def lookup(self, word):

        data = None
        soup = self.get_soup(word)
        data = self.__parse_soup(soup)

        # try:
        #     soup = self.get_soup(word)
        #     data = self.__parse_soup(soup)
        # except Exception as err:
        #    return f'Error during lookup: {err}'

        if data is None:
            return 'No match'

        root = data['root']

        def _def_print(d):
            head = word
            if word != root:
                head = f'{word} ({root})'
            detail = d['definition']
            e = d['example']
            if e is not None and e.strip() != '':
                detail = f'{detail}. "{e}"'
            return f'* {head}: {detail}'

        return  '\n\n'.join([ _def_print(d) for d in data['definitions'] ])


###############################
# Command-line check.

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Search term required')
        sys.exit(1)
    word = sys.argv[1]
    print(lookup(word))
