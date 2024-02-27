from botok.utils.lenient_normalization import remove_affixes, normalize_graphical, normalize_punctuation
from botok import normalize_unicode
from botok import tokenize_in_stacks
import re
import pyewts

EWTSCONVERTER = pyewts.pyewts()

def normalize_bo(s):
    if len(s) < 2:
        # otherwise bug in botok triggered, see
        # https://github.com/OpenPecha/Botok/commits/master/
        return s
    #s = normalize_unicode(s)
    # remove non-Tibetan
    s = re.sub(r"[^ༀ-࿚ ]+", "", s)
    s = normalize_graphical(s)
    s = normalize_punctuation(s).strip()
    return s

def make_lenient_bo(s):
    return s

# unnecessary
#EWTS_PARTS = re.compile(r"[bcdghjklmnprstvwyzBCDGHJKLMNPRSTVWYZ]*[-aeiouAIU*_ ]*")

def normalize_ewts(s):
    return EWTSCONVERTER.normalizeSloppyWylie(s)

def tokenize_ewts_base(query_s):
    # TODO: remove non-ewts:
    return EWTSCONVERTER.splitIntoTokens(query_s)
