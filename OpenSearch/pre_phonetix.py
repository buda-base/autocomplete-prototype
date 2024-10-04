# The idea is to find "mkhyen brtse'i dbang po" when user types "Khyentse Wangpo"

# To do this, we convert both the Wylie and the phonetics to an extremely lenient middle format, which must match exactly from both sides.
# The extreme leniency does not produce many false matches, because words are kept together and all words must match one field.
# If necessary, we can match phonetics only when we handle zero hits or seemingly poor results so that it will not interfere with queries in proper Wylie.

# At indexing time, Wylie is converted from "mkhyen brtse'i dbang po" to "gyen dse wang bo", which is indexed.
# At query time, user's phonetics are converted from "Khyentse Wangpo" to a query that has the structure:
# ("gyen dse" OR "gyen dsai" OR "gyan dse" OR "gyan dsai") AND "wang bo", which will match.

# USAGE:
# Index time: wylie_to_index = convert_to_fonetix(wylie_to_phonetics(wylie))
# Query time: query_to_match = fonetix_json(query_to_syllables(convert_to_fonetix(query)))

import re, unicodedata2

consonant = "[bcdghjklmnpqrstvwxyz']"
vowel = "[aeiou]"

# Both indexing time query time
# harmonize characters that can be ambiguous to one character
# "phurba nethik" -> "burba netig"
def convert_to_fonetix(string):
    string = string.lower()
    if not string or not re.search("[aeiou]", string):
        return ""
    # normalize diacritics
    string = ''.join(c for c in unicodedata2.normalize('NFKD', string) if not unicodedata2.combining(c))


    # First handle some irregular words
    # orgyen
    string = re.sub("[ou] ?rgy[ae]n", "o_gyen", string)
    # padma
    string = re.sub("p(ad|e)m([ao])", r"be m\2", string)
    string = re.sub("dalai", "da_la", string)
    string = re.sub("vajra", "ba_sra", string)
    string = re.sub("pa[gl]mo", "bag_mo", string)
    string = re.sub("dorje", "do_de", string)
    string = re.sub("ri[ngd]+zin", "rig_dzin", string)

	# remove r
    string = re.sub("(pa|po|ba|bo|wa|wo)r($|\s)", r"\1\2", string)

    # chimey -> chime
    string = re.sub("ey(\W|$)", r"e\1", string)
    # kurukulle -> kurukule
    string = re.sub(r"(.)\1+", r"\1", string)

    string = re.sub("kh*", "g", string)
    string = re.sub("th", "t", string)
    string = re.sub("sh", "s", string)
    string = re.sub("zh", "s", string)
    string = re.sub("ph", "p", string)
    string = re.sub("ch", "c", string)
    string = re.sub("dz", "s", string)
    string = re.sub("p", "b", string)
    string = re.sub("t", "d", string)
    string = re.sub("v", "b", string)
    string = re.sub("w", "b", string)
    string = re.sub("z", "s", string)

    return string

# Indexing time
# Convert wylie to some sort of phonetics
# Modified characters are converted to upper case to avoid processing them twice
def wylie_to_phonetics(string):
    def e_upper(match):
        return "E" + match.group(1).upper()

    # dbya -> DBYa
    def upper_except_vowels(match):
        replace = ""
        for char in match.group(1):
            if char not in vowel:
                replace += char.upper()
            else:
                replace += char
        return replace

    def simple_upper(match):
        return match.group(1).upper()

    # some common redundant chars
    string = re.sub("[/_:()]", " ", string)
    string = re.sub(" +", " ", string)
    string = re.sub("<.*?>", " ", string)
    
    # sanskrit does not work well
    string = string.lower()
    string = re.sub("\+", " ", string)
    string = re.sub("~", "", string)

    # a chung as the first character
    # bka' 'gyur, dge 'dun
    string = re.sub("'? '([gdk])", r"n \1", string) 
    # lo bzang
    string = re.sub("o b", "ob ", string)

    # ba wa
    # dwags
    string = re.sub("(" + consonant + "+)wa", r"\1a", string)
    string = re.sub("(^|\s)db(" + vowel + ")", r"\1W\2", string)
    # for the purpose of matching, use b for everything else
    string = re.sub(consonant + "*[bw](" + vowel + ")", r"B\1", string)

    # nga
    string = re.sub(consonant + "*ng(" + vowel + ")", r"NG\1", string)

    # y
    string = re.sub(consonant + "*ny(" + vowel + ")", r"NY\1", string)
    string = re.sub(consonant + "*my(" + vowel + ")", r"NY\1", string)
    string = re.sub(consonant + "*ky(" + vowel + ")", r"KY\1", string)
    string = re.sub(consonant + "*khy(" + vowel + ")", r"KHY\1", string)
    string = re.sub(consonant + "*gy(" + vowel + ")", r"GY\1", string)

    string = re.sub(consonant + "*phy(" + vowel + ")", r"CH\1", string)
    string = re.sub(consonant + "*py(" + vowel + ")", r"CH\1", string)
    string = re.sub("(?:^|\s|')by(" + vowel + ")", r"J\1", string)
    # the rest
    string = re.sub(consonant + "*y(" + vowel + ")", r"Y\1", string)

    # multi-chars (wa must be done before this)
    string = re.sub(consonant + "*ch*", "CH", string)
    string = re.sub(consonant + "*tsh", "TS", string)
    string = re.sub(consonant + "*ts", "TS", string)
    string = re.sub(consonant + "*sh", "SH", string)
    string = re.sub(consonant + "*dz", "DZ", string)
    string = re.sub(consonant + "*zh", "ZH", string)
    string = re.sub(consonant + "*th", "T", string)
    string = re.sub("sr(" + vowel + ")", "S\\1", string)
    string = re.sub(consonant + "*mr(" + vowel + ")", r"M\1", string)
    string = re.sub(consonant + "+r(" + vowel + ")", r"DR\1", string)
    string = re.sub(consonant + "*ph", "PH", string) # R to DR must be done
    string = re.sub(consonant + "*kh", "G", string)
    string = re.sub("(" + vowel + "ng" + consonant + "*)", upper_except_vowels, string)

    # simple consonants (ng, dr, sh, y, all *h must be done before)
    for char in "dhjklmnprstwgz":
        match = consonant + "*(" + char + vowel + ")"
        string = re.sub(match, upper_except_vowels, string)

    # al -> el (ng must be done)
    for char in "ds":
        match = "a(" + char + consonant + "*)"
        string = re.sub(match, e_upper, string)

    # vowels
    for char in "aeiou":
        match = "(" + char + consonant + "*)"
        string = re.sub(match, simple_upper, string, flags=re.IGNORECASE)

    # a chung (anything case sensitive must be done before)
    # remove 'i if not a'i
    string = re.sub("([eiou])'i", r"\1", string, flags=re.IGNORECASE)
    # a'i -> ai
    string = re.sub("(\s|^)(\S*)" + "a'i", r"\1\2AI", string, flags=re.IGNORECASE)
    string = re.sub(" +", " ", string)
    # remove all remaining apostrophes
    string = re.sub("'", "", string)

    # trailing s and d
    string = re.sub("[SD]($|\s)", r"\1", string)
    # gg
    string = re.sub("GG", "G", string)

    return string

# Query time
# divide modified query in syllables: "burba nedig" -> "bur_ba ne_dig"
def query_to_syllables(query):
    weights = {"lh": 1, "ha": 1, "da": 1, "an": 0.8056, "ng": 0.8429, "ce": 1, "be": 1, "ba": 1, "do": 1, "on": 0.8459, "ny": 0.9626, "ya": 1, "am": 0.7292, "me": 1, "sa": 1, "ag": 0.536, "gy": 0.9801, "se": 1, "en": 0.8625, "ge": 0.9971, "ab": 0.8361, "yi": 1, "mo": 0.9465, "la": 0.9994, "dz": 1, "ze": 1, "cu": 1, "go": 0.9911, "ne": 1, "un": 0.9204, "ga": 0.997, "gu": 0.99, "za": 1, "gh": 0.9857, "ho": 1, "or": 0.9678, "lo": 0.9954, "re": 0.9978, "mi": 1, "ig": 0.6066, "ye": 1, "el": 0.8097, "wa": 1, "ro": 0.9941, "ol": 0.7949, "de": 1, "ad": 0.0383, "di": 1, "ja": 1, "ma": 1, "hy": 1, "co": 1, "bo": 0.9965, "dr": 1, "ri": 1, "er": 0.7249, "ds": 1, "so": 1, "ju": 1, "zo": 1, "og": 0.6421, "yo": 1, "je": 1, "su": 1, "si": 1, "ci": 1, "ar": 0.7834, "in": 0.8573, "ji": 1, "rj": 0.8219, "we": 1, "il": 0.4226, "na": 0.9909, "ud": 0.0355, "db": 1, "al": 0.0808, "nu": 0.9615, "ur": 0.7747, "um": 0.8057, "im": 0.3208, "no": 0.9561, "wu": 1, "ug": 0.6412, "gi": 1, "ra": 1, "ru": 0.9982, "ub": 0.718, "du": 1, "zi": 1, "jo": 1, "eb": 0.1746, "ca": 1, "wi": 1, "iw": 0.018, "ul": 0.6783, "le": 0.9984, "om": 0.5882, "sl": 1, "em": 0.1769, "bu": 0.9846, "rg": 0.0705, "zu": 1, "ob": 0.3034, "lu": 0.9959, "eg": 0.2791, "yu": 1, "ai": 1, "ry": 0.1395, "wo": 1, "he": 1, "sr": 1, "aw": 0.0273, "li": 1, "hu": 1, "ir": 0.2071, "sw": 1, "ih": 0.2593, "ah": 0.3134, "lm": 0.1495, "oh": 0.1538, "hi": 1, "mu": 0.85, "nd": 0.0051, "ni": 0.9966, "ib": 0.1193, "zr": 1, "mh": 0.0833, "hr": 1, "bs": 0.0741, "au": 0.0208, "ac": 0.0017, "nr": 0.0099, "id": 0.0055, "gr": 0.0175, "as": 0.0135, "dy": 1, "ow": 0.0079, "sm": 1, "uh": 0.0588, "is": 0.0061, "sd": 1, "ly": 0.0417, "ed": 0.0022, "ae": 0.5, "es": 0.0052, "sy": 1, "uw": 0.0377, "ay": 0.0054, "ii": 1, "od": 0.0014, "gc": 0, "nb": 0, "mm": 0, "gg": 0, "bg": 0, "ec": 0.001, "gz": 0, "gb": 0, "nz": 0, "rl": 0, "lw": 0, "ld": 0, "ns": 0, "rc": 0, "gj": 0, "mg": 0, "nl": 0, "nc": 0, "lb": 0, "eo": 0.001, "oz": 0.001, "gd": 0, "oj": 0.001, "nj": 0, "mb": 0, "gs": 0, "uc": 0.001, "gl": 0, "os": 0.001, "gm": 0, "rm": 0, "oy": 0.001, "gw": 0, "ew": 0.001, "lg": 0, "gn": 0, "ml": 0, "rb": 0, "ls": 0, "nn": 0, "oc": 0.001, "ms": 0, "aj": 0.001, "md": 0, "bb": 0, "lj": 0, "rw": 0, "nw": 0, "us": 0.001, "iu": 0.001, "ez": 0.001, "bn": 0, "rn": 0, "eu": 0.001, "ij": 0.001, "rd": 0, "ej": 0.001, "nm": 0, "mc": 0, "uj": 0.001, "rs": 0, "bd": 0, "ey": 0.001, "iy": 0.001, "mn": 0, "bl": 0, "mj": 0, "ou": 0.001, "iz": 0.001, "ic": 0.001, "ll": 0, "bm": 0, "ao": 0.001, "mz": 0, "bj": 0, "uo": 0.001, "mr": 0, "bc": 0, "eh": 0.001, "by": 0, "lz": 0, "bw": 0, "lr": 0, "az": 0.001, "br": 0, "hs": 0, "ln": 0, "hd": 0, "lc": 0, "uz": 0.001, "aa": 0.001, "uy": 0.001, "my": 0, "rr": 0, "rz": 0, "mw": 0, "nh": 0, "hg": 0, "rh": 0, "io": 0.001, "bz": 0, "dw": 0, "oo": 0.001, "oa": 0.001, "ea": 0.001, "ia": 0.001}
    new_query = ""
    for word in re.findall("\S+", query):
        # word has one vowel
        if len(re.findall("[aeiou]", word)) <= 1:
            new_query += word + " "
        # word has many vowels
        else:
            # plan cut points
            is_it_here = []
            vowel_positions = []
            for i in range(0, len(word) - 1):
                # add weight to list
                pair = word[i] + word[i+1]
                if pair in weights:
                    is_it_here.append(weights[pair])
                else:
                    is_it_here.append(0.5)
                    #print(f'"{pair}" does not have a weight')
                # mark vowels
                if word[i] in "aeiou":
                    vowel_positions.append(i)
            # if word ends in vowel
            if word[-1] in "aeiou":
                vowel_positions.append(len(word))
            
            # cut the word in syllables
            was_cut_at = 0
            for i in range(0, len(vowel_positions) - 1):
                togetherness = is_it_here[vowel_positions[i]:vowel_positions[i+1]]
                cut_at = vowel_positions[i] + togetherness.index(min(togetherness)) + 1
                # add the cut part as a separate word to new query
                new_query += word[was_cut_at:cut_at] + "_"
                was_cut_at = cut_at
            # add the rest as a new word
            if was_cut_at < len(word):
                new_query += word[was_cut_at:] + "_"
            new_query += " "
    # clean up underscores
    new_query = re.sub("_( |$|_)", r"\1", new_query)

    return new_query.strip()

# Query time
# Create the query json with some last orring of pal/pel, a/a'i
def fonetix_json(query):
    # variations of each word
    full_query = []
    for word in re.split(" ", query):
        one_word = []
        for syllable in re.split("_", word):
            one_syllable = []
            # syllable as typed
            one_syllable.append(syllable)
            # pel, pen to pal, pan
            palden, n = re.subn("e([nl])$", r"a\1", syllable)
            if n:
                one_syllable.append(palden)
            # e to ai
            ai, n = re.subn("[ae]$", r"ai", syllable)
            if n:
                one_syllable.append(ai)
            #[[pal, pel],[dan, den]]
            one_word.append(one_syllable)
        full_query.append(one_word)
    # create the opensearch json
    # full query = [[["ben", "ban"], ["cen", "can"]], [["la", "lai"], ["ma", "mai"]]]

    def generate_combinations_rec(lists):
        if len(lists) == 0:
            return [[]]
        rest_combinations = generate_combinations_rec(lists[1:])
        return [[item] + rest for item in lists[0] for rest in rest_combinations]

    must = []
    for word in full_query:
        combinations = generate_combinations_rec(word)
        # Create a 'should' clause with all the combinations
        should = [
            {
                "multi_match": {
                    "query": " ".join(combination),
                    "fields": ["prefLabel_prePhon", "altLabel_prePhon"],
                    "type": "phrase"
                }
            } 
            for combination in combinations
        ]
        # Add the should clause to the must clauses
        must.append({"bool": {"should": should}})

    json_obj = {"bool": {"must": must}}
    return json_obj

if __name__ == '__main__':
    checklist = [
        ("ta la'i bla ma", "Dalai Lama"),
        ("pad+ma 'byung gnas","Padma Jungné"),
        ("bstan 'dzin rgya mtsho", "Tenzin Gyatso"),
        ("paN chen bla ma", "Penchen Lama"),
        ("phur pa'i gnad tig", "purba netik"),
        ("'jam dbyangs mkhyen brtse'i dbang po", "Jamyang Khyentse Wangpo"),
        ("mar pa lo tsA ba", "Marpa Lotsawa"),
        ('mtsho skar rgyal mtshan', "Tsokar Gyaltsen"),
        ("pad+ma 'byung gnas", "Padma Jungné"),
        ("ta la'i bla ma", "Dalai Lama"),
        ("nopossible match", "asdfadsf"),
        ("bsam sding rdo rde phag mo","Samding Dorje Phagmo"),
        ("shlo ka", "shloka"),
        ("paN+Di+ta", "pandita"),
        ("shrI", "Sri"),
        ("ba dzra", "Vajra"),
        ("o rgyan", "Orgyen"),
        ("spyan ras gzigs", "Chenrezig"),
        ("bstan 'dzin rgya mtsho", "Tenzin Gyatso"),
        ("mkha' 'gro snying thig","Khandro Nyingtik")
    ]

    for wylie, query in checklist:
        print()
        print(f'"{wylie}" "{query}"')
        os_json = fonetix_json(query_to_syllables(convert_to_fonetix(query)))
        query_fonetix = convert_to_fonetix(wylie_to_phonetics(wylie))
        for one_word in os_json['bool']['must']:
            fine = False
            variations = one_word['bool']['should']
            for n in range(0, len(variations)):
                variation = variations[n]['match']['fonetix']
                if re.search(f'(^| ){variation}($| )', query_fonetix):
                    fine = True
            if not fine:
                input(f'\nNO MATCH FOR "{variations}" in "{query_fonetix}"')
        if fine:
            print(os_json)
            input('MATCH')

