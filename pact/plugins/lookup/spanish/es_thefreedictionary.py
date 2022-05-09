"""Monolingual definitions and examples from es_thefreedictionary.es

Only includes data from 'ds-single', where not <strong> entries.  See
comments for details.
"""

from bs4 import BeautifulSoup as bs
import re
from requests import get
import sys


def __extract_definition_and_illustration(soup):

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
    

    # s = soup.find('<i>').replaceWith('[')
    # Remove numbering from the text.
    definition = re.sub('^\d+\. ', '', soup.text)

    return {
        'definition': f'{definition.strip()}{syn}{ant}',
        'example': '; '.join(illustrations).strip()
    }


def __get_soup(url):
    raw = get(url).content.decode('utf-8')

    # During dev, save to and then read from a file,
    # saves time.
    # with open('dumpfile.html', 'w') as f:
    #   f.write(raw)
    # with open('dumpfile.html', 'r') as f:
    #    raw = f.read()
    # print(raw)

    soup = bs(raw, features='html.parser')

    maintext = soup.select("#MainTxt")[0]

    rootnode = maintext.select("#Definition h2")
    if len(rootnode) == 0:
        return None
    
    root = rootnode[0].text.strip()

    definitions = []
    for c in [ 'ds-single' ]:
        definitions += maintext.select(f"#Definition div.{c}")
    # Previously had included ['ds-list', 'sds-list'] in the loop, but
    # that returned not great entries.  This suffices for now.

    definitions = [
        __extract_definition_and_illustration(d)
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


def lookup(word):

    query_url = f"https://es.thefreedictionary.com/{word}"
    data = None
    try:
        data = __get_soup(query_url)
    except Exception as err:
        return f'Error during lookup: {err}'

    if data is None:
        return 'No match'

    def _def_print(d):
        ret = d['definition']
        e = d['example']
        if e is not None and e.strip() != '':
            ret = f'{ret}. "{e}"'
        return f'* {word}: {ret}'

    return  '\n\n'.join([ _def_print(d) for d in data['definitions'] ])


###############################
# Command-line check.

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Search term required')
        sys.exit(1)
    word = sys.argv[1]
    print(lookup(word))
