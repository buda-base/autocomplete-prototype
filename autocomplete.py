from encoder import Encoder
from generictrie import Trie, Node
import logging
import pyewts
from index_builder import get_index

EWTSCONVERTER = pyewts.pyewts()

#logging.basicConfig(level=logging.DEBUG)

def get_proper_start_i(query_s):
    """
    removes prefixes that we'll ignore, such as anything non-Tibetan
    plus the prefixes listed in 
    https://github.com/buda-base/lds-pdi/blob/master/src/main/java/io/bdrc/ldspdi/rest/controllers/ReconciliationController.java#L186
    returns the index of the first character to be considered
    """
    return 0


def auto_complete(query_s, res_limit=10, index_name="bo_general"):
    """
    The main function. Returns a list of 10 results in the following format:
    {
       "res": "<ignored>foo </ignored>ba<suggested>r</suggested>",
       "lang": "bo",
       "category": "Person"
    }
    """
    first_c_idx = get_proper_start_i(query_s)
    unprefixed_query = query_s[first_c_idx:]
    index = get_index(index_name)
    query_tokens, final_token_candidates_encoded = index.tokenize_query(unprefixed_query)
    logging.debug("query tokens: %s", query_tokens)
    logging.debug("final token candidates: %s", [index.encoder.decode(ord(i)) for i in final_token_candidates_encoded])
    encoded_query = index.encoder.encode_list(query_tokens)
    logging.debug("encoded query: '%s' (%s)", encoded_query, [ord(c) for c in encoded_query])
    suggestions = index.trie.get_top_10_suffixes(encoded_query, final_token_candidates_encoded)
    res = []
    base_res_str = ""
    if first_c_idx > 0:
        base_res_str = "<ignored>" + query_s[:first_c_idx] + "</ignored>"
    base_res_str += "".join(query_tokens)
    lng = "bo" if index_name == "bo_general" else "bo-x-ewts"
    for s in suggestions:
        encoded_suffix, encoded_category, score = s
        category = index.cat_encoder.decode(encoded_category)
        suffix = index.encoder.decode_string(encoded_suffix)
        res_str = base_res_str
        if suffix:
            res_str += "<suggested>" + suffix + "</suggested>"
        res.append({
            "res": res_str,
            "lang": lng,
            "category": category
            })
    return res

if __name__ == "__main__":
    #print(auto_complete("བཀའ་འགྱུར།"))
    #print(auto_complete("བཀའ་འགྱ"))
    print(auto_complete("bka' '", index_name="ewts_general"))
    #print(auto_complete("བཀའ་འགྱ"))