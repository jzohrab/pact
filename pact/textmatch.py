import re
import string
import Levenshtein as lev
from fuzzywuzzy import fuzz

# Spanish punct
punctuation = string.punctuation + '¿¡'


def tokenize(text):
    ret = []
    curr_token = None

    curr_pos = -1

    for c in text:
        curr_pos += 1
        if c.isalnum():
            if curr_token:
                curr_token['token'] += c
            else:
                curr_token = {
                    'pos': curr_pos,
                    'token': c,
                    'pre': None,
                    'post': None
                }
        else:
            if curr_token:
                curr_token['cleaned'] = cleaned_text(curr_token['token'])
                ret.append(curr_token)
            curr_token = None

    if curr_token:
        curr_token['cleaned'] = cleaned_text(curr_token['token'])
        ret.append(curr_token)

    # Add punctuation onto each token
    def prepunct(pos):
        p = pos - 1
        while p >= 0 and text[p] in punctuation:
            p -= 1
        if (p+1 < pos):
            return text[p + 1 : pos]
        else:
            return None

    def postpunct(pos):
        p = pos
        while p < len(text) and text[p] in punctuation:
            p += 1
        if (p > pos):
            return text[pos : p]
        else:
            return None

    for r in ret:
        r['pre'] = prepunct(r['pos'])
        r['post'] = postpunct(r['pos'] + len(r['token']))

    return ret


def cleaned_text(t):
    s = re.sub('[\W_]+', ' ', t, flags=re.UNICODE)
    return s.casefold().strip()


def find_sentences(full_text, search_for):
    # Finds array of matches
    # - (matched_text, score, (rawstart, rawend), (start, end), context)
    return 'hello'


def calc_score(bounds, tokens, cleaned_search, include_text_in_results = False):
    tokens_in_bounds = tokens[bounds[0] : bounds[1]]
    text = ' '.join([tok['cleaned'] for tok in tokens_in_bounds])
    distance = lev.distance(text, cleaned_search)
    # ratio = round(lev.ratio(text, cleaned_search), 3)

    fuzzy_ratio = fuzz.ratio(text, cleaned_search)

    ret = {
        'bounds': bounds,
        'distance': distance,
        'fuzzy_ratio': fuzzy_ratio
    }
    if include_text_in_results:
        ret['text'] = text
    return ret


def calc_raw(text, search_for, include_text_in_results = False):
    tokens = tokenize(text)
    def token_index_groups(n):
        fixed_n = min(max(1, n), len(tokens))
        return ([i, i+fixed_n] for i in range(0, len(tokens) - fixed_n + 1))

    cleaned_search = cleaned_text(search_for)

    search_tok_count = len(cleaned_search.split(' '))
    minlen = max(1, int(search_tok_count * 0.75) - 5)
    maxlen = min(len(tokens), int(search_tok_count * 1.25) + 5)
    for search_len in range(minlen, maxlen):
        for bounds in token_index_groups(search_len):
            yield calc_score(bounds, tokens, cleaned_search, include_text_in_results)



def string_from_tokens(text, tokens, bounds):
    def tok_to_string(t):
        return f"{t['pre'] or ''}{t['token']}{t['post'] or ''}"
    first = tokens[bounds[0]]
    last = tokens[bounds[1] - 1]
    textpart = text[ first['pos'] : (last['pos'] + len(last['token'])) ]
    return f"{first['pre'] or ''}{textpart}{last['post'] or ''}"


def candidates(text, sought, include_text_in_results = False, min_fuzzy_ratio = 50):
    results = list(calc_raw(text, sought, include_text_in_results))
    mindist = min([r['distance'] for r in results])

    def is_candidate(r):
        return (
            r['distance'] == mindist
            and r['fuzzy_ratio'] > min_fuzzy_ratio
        )

    candidates = [ r for r in results if is_candidate(r) ]
    return sorted(candidates, key = lambda r: r['bounds'][0])


def sentences_bounding_positions(text, startpos, endpos):
    # Assumption: sentences are properly spaced.
    #
    # e.g., this is not:
    #    This is the start."Note no sentence space after the period."

    if startpos < 0 or startpos > len(text):
        raise Exception('bad startpos')
    if endpos < 0 or endpos > len(text):
        raise Exception('bad endpos')
    if endpos < startpos:
        raise Exception('endpos must be >= startpos')

    soft_enders = ".!?"  # Might have a quote afterwards
    hard_enders = "\n"  # No quote
    enders = soft_enders + hard_enders

    # count back from startpos until hit an ender.
    p = startpos
    while p >= 0 and text[p] not in enders:
        p -= 1
    if p < 0:
        # Use start of text.
        p = 0
    else:
        # Move past the ender.
        p += 1

        # Move after quote immed. following soft ender.
        if text[p - 1] in soft_enders and text[p] == '"':
            p += 1
    sentences_start = p

    # count forward from endpos until hit an ender.
    p = endpos
    while p < len(text) and text[p] not in enders:
        p += 1
    if p >= len(text):
        # Use end of text.
        p = len(text)
    else:
        # Move past the ender.
        p += 1

        # Move after quote immed. following soft ender.
        if text[p - 1] in soft_enders and p < len(text) and text[p] == '"':
            p += 1
    sentences_end = p

    ret = text[ sentences_start : sentences_end ]

    return ret.strip()


def search(text, sought, include_details = False, min_fuzzy_ratio = 50):
    tokens = tokenize(text)
    cands = candidates(text, sought, True, min_fuzzy_ratio)

    def __get_context(candidate):
        startc, endc = candidate['bounds']
        startp = tokens[startc]['pos']
        endp = tokens[endc - 1]['pos']
        return sentences_bounding_positions(text, startp, endp)

    def __get_result(c):
        ret = {
            'match': string_from_tokens(text, tokens, c['bounds']),
            'context': __get_context(c),
        }
        if include_details:
            for k in ('distance', 'fuzzy_ratio'):
                ret[k] = c[k]
        return ret

    return [ __get_result(c) for c in cands ]



def ellipsify(partial, fulltext):
    pos = fulltext.find(partial)
    if pos == -1:
        # Not found.
        return partial

    left = fulltext[0 : pos].strip()
    if left != '':
        left = f'[{left}]'
        if fulltext[pos - 1] == ' ':
            left += ' '
    right = fulltext[pos + len(partial):].strip()
    if right != '':
        right = f'[{right}]'
        if fulltext[pos + len(partial)] == ' ':
            right = f' {right}'

    return f'{left}{partial}{right}'
