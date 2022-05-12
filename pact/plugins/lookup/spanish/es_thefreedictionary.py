"""Monolingual definitions and examples from es_thefreedictionary.es"""

import os
import inspect
import sys

# Sheesh python is a drag sometimes.
# https://stackoverflow.com/questions/714063/importing-modules-from-parent-folder
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import utils

def lookup(word):

    d = utils.TheFreeDictionary(
        url = 'https://es.thefreedictionary.com',
        include_section_data_src = [ 'Larousse_GDLE' ],
        root_tag = 'h2',
        include = [ 'div.ds-single', 'div.ds-list' ]
    )

    return d.lookup(word)


###############################

if __name__ == '__main__':
    print(lookup(sys.argv[1]))
