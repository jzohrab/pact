"""Sample lookup.
"""

def lookup(term = 'example'):
    result = f"""Results of looking up {term}:

1. definition
example

2. definition
example

Note: the plugin can return results however it wants, it's just shown
in a tkinter text widget."""

    return result

if __name__ == '__main__':
    print(lookup('something'))
