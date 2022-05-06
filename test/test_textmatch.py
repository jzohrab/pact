import unittest
import sys
import os

sys.path.append(os.path.abspath(sys.path[0]) + '/../')
from pact.textmatch import *


# Test helpers.
def token(tok, pos, pre=None, post=None):
    return {
        'token': tok,
        'cleaned': cleaned_text(tok),
        'pos': pos,
        'pre': pre,
        'post': post
    }

def tokens(tups):
    return [ token(*tup) for tup in tups ]


class TestMatcher_tokenize(unittest.TestCase):

    def assertTokenized(self, txt, tups):
        actual = tokenize(txt)
        self.assertEqual(actual, tokens(tups))

    def test_single_word(self):
        self.assertTokenized("Tienes", [('Tienes', 0)])

    def test_two_word(self):
        self.assertTokenized(
            "Tienes uno",
            [('Tienes', 0),('uno',7)]
        )

    def test_single_word_with_punct(self):
        self.assertTokenized(
            "\"¿Tienes?\"",
            [('Tienes', 2, '"¿', '?"')]
        )

    def test_full_sentence(self):
        sentence = "   \"¿Tienes 12 móvil?\" \n!!!\n***"
        self.assertTokenized(
            sentence,
            [
                ('Tienes', 5, '"¿'),
                ('12', 12),
                ('móvil', 15, None, '?"')
            ]
        )


class TestMatcher_cleaned_text(unittest.TestCase):

    def test_cleaned_text(self):
        actual = cleaned_text("   \"¿Tienes 12 un móvil?\" \"Sí, tengo uno.\"\n!!!\n***")
        expected = 'tienes 12 un móvil sí tengo uno'
        self.assertEqual(actual, expected)


class TestMatcher_calc_raw(unittest.TestCase):

    def sorted_results(self, r):
        def distance(d): return d['distance']
        return sorted(r, key=distance)

    def assert_raw_equals(self, actual, expected):
        self.assertEqual(self.sorted_results(actual), self.sorted_results(expected))

    def test_single_letter_match(self):
        self.maxDiff = None
        text = 'a b c d'
        sought = 'c'
        matches = calc_raw(text, sought, include_text_in_results = True)
        expected = [
            {'bounds': [2, 3], 'distance': 0, 'text': 'c', 'fuzzy_ratio': 100},
            {'bounds': [0, 1], 'distance': 1, 'text': 'a', 'fuzzy_ratio': 0},
            {'bounds': [1, 2], 'distance': 1, 'text': 'b', 'fuzzy_ratio': 0},
            {'bounds': [3, 4], 'distance': 1, 'text': 'd', 'fuzzy_ratio': 0},
            {'bounds': [1, 3], 'distance': 2, 'text': 'b c', 'fuzzy_ratio': 50},
            {'bounds': [2, 4], 'distance': 2, 'text': 'c d', 'fuzzy_ratio': 50},
            {'bounds': [0, 2], 'distance': 3, 'text': 'a b', 'fuzzy_ratio': 0},
            {'bounds': [0, 3], 'distance': 4, 'text': 'a b c', 'fuzzy_ratio': 33},
            {'bounds': [1, 4], 'distance': 4, 'text': 'b c d', 'fuzzy_ratio': 33}
        ]
        self.assert_raw_equals(matches, expected)

    def test_cal_raw_ignores_caps_punct_and_whitespace(self):
        self.maxDiff = None
        plain =    calc_raw('a b c d', 'c', include_text_in_results = True)
        notplain = calc_raw('A. B. C! D', 'c', include_text_in_results = True)
        self.assertEqual(self.sorted_results(plain), self.sorted_results(notplain))



class TestMatcher_candidates(unittest.TestCase):

    def test_single_letter_match(self):
        self.maxDiff = None
        text = 'a b c d'
        sought = 'c'
        actual = candidates(text, sought, include_text_in_results = True)
        expected = [
            {'bounds': [2, 3], 'distance': 0, 'text': 'c', 'fuzzy_ratio': 100}
        ]
        self.assertEqual(actual, expected)

    def test_two_matches(self):
        self.maxDiff = None
        text = 'a b c c'
        sought = 'c'
        actual = candidates(text, sought, include_text_in_results = True)
        expected = [
            {'bounds': [2, 3], 'distance': 0, 'text': 'c', 'fuzzy_ratio': 100},
            {'bounds': [3, 4], 'distance': 0, 'text': 'c', 'fuzzy_ratio': 100},
        ]
        self.assertEqual(actual, expected)

    def test_closest_match_is_candidate(self):
        self.maxDiff = None
        text = 'axx bxx caa cbb'
        sought = 'ccc'
        actual = candidates(text, sought, include_text_in_results = True, min_fuzzy_ratio = 30)
        expected = [
            {'bounds': [2, 3], 'distance': 2, 'text': 'caa', 'fuzzy_ratio': 33},
            {'bounds': [3, 4], 'distance': 2, 'text': 'cbb', 'fuzzy_ratio': 33},
        ]
        self.assertEqual(actual, expected)

    def test_no_matches_means_no_candidates(self):
        self.maxDiff = None
        text = 'axx bxx caa cbb'
        sought = 'ddd'
        actual = candidates(text, sought, include_text_in_results = True)
        expected = []
        self.assertEqual(actual, expected)

    def test_multiword_search(self):
        self.maxDiff = None
        text = 'axx bxx caa cdd'
        sought = 'ccc ddd'
        actual = candidates(text, sought, include_text_in_results = True)
        expected = [
            {'bounds': [2, 4], 'distance': 3, 'text': 'caa cdd', 'fuzzy_ratio': 57}
        ]
        self.assertEqual(actual, expected)


class TestMatcher_join_token_range(unittest.TestCase):

    def setUp(self):
        self.sentence = "   \"¿Tienes 12 un móvil?\" \"Sí, tengo uno.\"\n!!!\n***"
        self.tokens = tokenize(self.sentence)

    def assert_string_from_tokens_equals(self, bounds, expected):
        actual = string_from_tokens(self.sentence, self.tokens, bounds)
        self.assertEqual(actual, expected, bounds)

    def test_bounds(self):
        self.assert_string_from_tokens_equals([2, 4], "un móvil?\"")
        self.assert_string_from_tokens_equals([1, 4], "12 un móvil?\"")
        self.assert_string_from_tokens_equals([0, 7], "\"¿Tienes 12 un móvil?\" \"Sí, tengo uno.\"")


class TestMatcher_sentence_bounding_positions(unittest.TestCase):

    def test_cases(self):
        # Each case should have only one 'i' !!!!
        cases = [
            ["Hi there.", "Hi there."],
            ["Start. Middle. End.", 'Middle.'],
            ['"Start." "Middle." "End."', '"Middle."'],
            ['. hi', 'hi'],
            ['." hi', 'hi'],
            ["\n hi", 'hi'],
            ['." hi.', 'hi.'],
            ['." "hi."', '"hi."'],
            ['." hi. hello', 'hi.'],
            ['hi."', 'hi."'],
            ['." "hi." "hello."', '"hi."'],
            ['"Hi,", he yelled.', '"Hi,", he yelled.']
        ]
        for text, expected in cases:
            p = text.index('i')
            actual = None
            try:
                actual = sentences_bounding_positions(text, p, p)
            except Exception as e:
                actual = '???'
                print()
                print(e)
                print((text, expected))
                print()
            self.assertEqual(actual, expected)


    def test_complex(self):
        text = 'A full sentence.\nX: "Hi." Y: "Hello!"\nParagraph breaks -\nOK.'
        # positions (note \n is 1 char)
        #       0         10        20         30         40        50
        #       01234567890123456 789012345678901234567 8901234567890123456 789

        cases = [
            [6, 6, "A full sentence."],
            [1, 6, "A full sentence."],
            [0, 6, "A full sentence."],
            [0, 15, "A full sentence."],
            [20, 20, 'X: "Hi."'],
            [30, 30, 'Y: "Hello!"'],
            [40, 40, 'Paragraph breaks -'],
            [58, 58, 'OK.'],
            [12, 22, 'A full sentence.\nX: "Hi."'],
            [32, 44, 'Y: "Hello!"\nParagraph breaks -'],

            # Exceptions -- there are better ways to write this, but this works fine.
            [44, 32, 'error: endpos must be >= startpos'],
            [-10, -5, 'error: bad startpos'],
            [0, 10000, 'error: bad endpos'],
            [-10, 5000, 'error: bad startpos'],
        ]
        for startpos, endpos, expected in cases:
            actual = None
            try:
                actual = sentences_bounding_positions(text, startpos, endpos)
            except Exception as e:
                actual = f'error: {e}'
                # print()
                # print(e)
                # print((startpos, endpos, text, expected, actual))
                # print()
            self.assertEqual(actual, expected)


class TestMatcher_search(unittest.TestCase):

    def test_search_characterization(self):
        """Not really a test, just ensuring stability."""
        self.maxDiff = None
        text = """Here is some text.  With lots of info.  Search for this.  Search for something else."""
        cases = [
            ["Search for another thing", [
                {'match': 'Search for something', 'context': 'Search for something else.'}
            ]],
            ["some info", [
                {'match': 'of info.', 'context': 'With lots of info.'}
            ]],
            [ "bits of info search", [
                {'match': 'lots of info.  Search', 'context': 'With lots of info.  Search for this.'}
            ]],
            ["for", [
                {'match': 'for', 'context': 'Search for this.'},
                {'match': 'for', 'context': 'Search for something else.'}
            ]],
            [ "yyy", [] ]
        ]
        for c in cases:
            actual = search(text, c[0], False)
            # print(actual)
            self.assertEqual(actual, c[1])


    def test_search_characterization_with_details(self):
        """Not really a test, just ensuring stability."""
        self.maxDiff = None
        text = """Here is some text.  With lots of info.  Search for this.  Search for something else."""
        sought = "Search for another thing"
        expected = [
            {
                'match': 'Search for something',
                'context': 'Search for something else.',
                'distance': 6,
                'fuzzy_ratio': 82
            }
        ]

        actual = search(text, sought, True)
        # print(actual)
        self.assertEqual(actual, expected)


class TestMatcher_ellipsify(unittest.TestCase):

    def test_ellipsify(self):
        cases = [
            [ "bear", "apple bear cat", "[apple] bear [cat]" ],
            [ "bear", "apple bear", "[apple] bear" ],
            [ "bear", "apple bear   ", "[apple] bear" ],
            [ "bear", "    apple bear", "[apple] bear" ],
            [ "bear", "bear cat", "bear [cat]" ],
            [ "bear", "bear cat   ", "bear [cat]" ],

            # Partials
            [ "be", "apple bear", "[apple] be[ar]" ],
            [ "be", "applebee's", "[apple]be[e's]" ],

            # No match = leave as-is
            [ "xxx leave as-is", "apple bear", "xxx leave as-is" ],
            [ "beggar", "apple bear cat", "beggar" ],
        ]
        for c in cases:
            actual = ellipsify(c[0], c[1])
            self.assertEqual(actual, c[2])


if __name__ == '__main__':
    unittest.main()
