from botok.utils.lenient_normalization import remove_affixes, normalize_graphical, normalize_punctuation
from botok import normalize_unicode
from botok import tokenize_in_stacks
import re
from fontTools import unicodedata
import pyewts

EWTSCONVERTER = pyewts.pyewts()

def get_main_script_tag(text: str):
    """
    return the ISO 15924 tag of the main script used
    in a string
    """
    halflen = int(len(text) / 2)
    scripts = {}
    maxcharscript_nbchars = 0
    maxcharscript = "Zyyy"
    for i, c in enumerate(text):
        cscript = unicodedata.script(c)
        if cscript not in scripts:
            scripts[cscript] = 0
        script_nbchars = scripts[cscript] + 1
        scripts[cscript] = script_nbchars
        if script_nbchars > maxcharscript_nbchars:
            maxcharscript_nbchars = script_nbchars
            maxcharscript = cscript
        if maxcharscript_nbchars > halflen:
            return maxcharscript
    return maxcharscript

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
