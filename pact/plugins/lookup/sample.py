"""Sample lookup.
"""

def lookup(term = 'example'):
    return f"""DEMONSTRATION ONLY.

This is a sample lookup implementation, in
pact/plugins/lookup/sample.py.

Change the lookup module by updating config.ini,
[Pact][LookupModule]."""


if __name__ == '__main__':
    print(lookup('something'))
