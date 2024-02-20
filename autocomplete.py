from botok import normalize_unicode
from botok import tokenize_in_stacks
from botok.utils.lenient_normalization import remove_affixes, normalize_graphical, normalize_punctuation
from encoder import Encoder
from generictrie import Trie, Node
import csv
import logging

#logging.basicConfig(level=logging.DEBUG)

def normalize_bo(s):
	s = normalize_unicode(s)
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

def get_proper_start_i(query_s):
	"""
	removes prefixes that we'll ignore, such as anything non-Tibetan
	plus the prefixes listed in 
	https://github.com/buda-base/lds-pdi/blob/master/src/main/java/io/bdrc/ldspdi/rest/controllers/ReconciliationController.java#L186
	returns the index of the first character to be considered
	"""
	return 0

SAVED_INDEXES = {}

def get_index(index_name):
	if index_name in SAVED_INDEXES:
		return SAVED_INDEXES[index_name]
	encoder = Encoder(allow_decode=True)
	cat_encoder = Encoder(allow_decode=True)
	partial_to_full = {}
	trie = Trie(encoder)
	fname = "input_bo_categories_kangyur.csv"
	with open(fname, newline='') as csvfile:
	    csvreader = csv.reader(csvfile)
	    for row in csvreader:
	        s = normalize_unicode(row[0])
	        score = int(row[1])
	        encoded_cat = cat_encoder.encode(row[2])
	        token_list = tokenize_in_stacks(s)
	        encoded_token_list = ""
	        for t in token_list:
	        	encoded_t = encoder.encode(t)
	        	encoded_token_list += chr(encoded_t)
	        	# fill partial_to_full
	        	for i in range(1, len(t)):
	        		partial = t[i:]
	        		if partial not in partial_to_full:
	        			partial_to_full[partial] = set()
	        		partial_to_full[partial].add(t)
	        trie.add(encoded_token_list, score, encoded_cat)
	return trie, encoder, partial_to_full, cat_encoder

def auto_complete(query_s, res_limit=10, index_name="bo_all"):
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
	trie, encoder, partial_to_full, cat_encoder = get_index(index_name)
	query_tokens, final_token_candidates_encoded = tokenize_bo(unprefixed_query, partial_to_full)
	logging.debug("query tokens: %s\nfinal token candidates encoded: %s", query_tokens, final_token_candidates_encoded)
	encoded_query = encoder.encode_list(query_tokens)
	logging.debug("encoded query: %s", encoded_query)
	suggestions = trie.get_top_10_suffixes(encoded_query, final_token_candidates_encoded)
	res = []
	base_res_str = ""
	if first_c_idx > 0:
		base_res_str = "<ignored>" + query_s[:first_c_idx] + "</ignored>"
	base_res_str += unprefixed_query
	for s in suggestions:
		encoded_suffix, encoded_category, score = s
		category = cat_encoder.decode(encoded_category)
		suffix = encoder.decode_string(encoded_suffix)
		res_str = base_res_str
		if suffix:
			res_str += "<suggested>" + suffix + "</suggested>"
		res.append({
			"res": res_str,
			"lang": "bo",
			"category": category
			})
	return res

if __name__ == "__main__":
	print(auto_complete("བཀའ་འགྱུར།"))