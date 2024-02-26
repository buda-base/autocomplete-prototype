from botok.utils.lenient_normalization import remove_affixes, normalize_graphical, normalize_punctuation
from botok import normalize_unicode
from botok import tokenize_in_stacks

def normalize_bo(s):
    if len(s) < 2:
        # otherwise bug in botok triggered, see
        # https://github.com/OpenPecha/Botok/commits/master/
        return s
    #s = normalize_unicode(s)
    s = normalize_graphical(s)
    s = normalize_punctuation(s).strip()
    # TODO: remove everything non-Tibetan
    return s

def make_lenient_bo(s):
    return s

def tokenize_bo(query_s, partial_to_full):
    """
    returns a list of tokens, checks if the last token is complete or not
    """
    query_s = normalize_bo(query_s)
    stack_list = tokenize_in_stacks(query_s)
    final_stack = stack_list[-1]
    last_token_candidates = []
    if final_stack in partial_to_full:
        stack_list = stack_list[:-1]
        last_token_candidates = partial_to_full[final_stack]
    return stack_list, last_token_candidates