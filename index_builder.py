import pickle
from encoder import Encoder
from generictrie import Trie
import logging
from pathlib import Path
import csv
import pyewts
from utils import normalize_bo, normalize_ewts, tokenize_ewts_base
from botok import tokenize_in_stacks
import sys
from threading import Lock

sys.setrecursionlimit(10000)

EWTSCONVERTER = pyewts.pyewts()

SAVED_INDEXES = {}

class Index:
    def __init__(self, trie, encoder, partial_to_full, cat_encoder):
        self.trie = trie
        self.encoder = encoder
        self.partial_to_full = partial_to_full
        self.cat_encoder = cat_encoder
        self.query_tokenize_fun = None

    def tokenize_query(self, s):
        token_list = self.query_tokenize_fun(s)
        final_stack = token_list[-1]
        last_token_candidates = []
        if final_stack in self.partial_to_full:
            token_list = token_list[:-1]
            last_token_candidates = self.partial_to_full[final_stack]
        return token_list, last_token_candidates

def bo_tokenize_to_bo(s):
    s = normalize_bo(s)
    return tokenize_in_stacks(s)

def ewts_tokenize_to_bo(s):
    s = EWTSCONVERTER.toUnicode(s)
    s = normalize_bo(s)
    return tokenize_in_stacks(s)

def ewts_tokenize_to_ewts(s):
    s = normalize_ewts(s)
    return tokenize_ewts_base(s)

def index_from_csv(csv_fname, value_to_tokens_fun):
    logging.info("build index from %s", csv_fname)
    encoder = Encoder(allow_decode=True)
    cat_encoder = Encoder(allow_decode=True)
    partial_to_full = {}
    trie = Trie(encoder)
    with open(csv_fname, newline='') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            score = int(row[1])
            encoded_cat = cat_encoder.encode(row[2])
            token_list = value_to_tokens_fun(row[0])
            encoded_token_list = ""
            for t in token_list:
                encoded_t = encoder.encode(t)
                encoded_token_list += chr(encoded_t)
                # fill partial_to_full
                for i in range(1, len(t)+1):
                    partial = t[:i]
                    if partial not in partial_to_full:
                        partial_to_full[partial] = set()
                    partial_to_full[partial].add(chr(encoded_t))
            trie.add(encoded_token_list, score, encoded_cat)
    return Index(trie, encoder, partial_to_full, cat_encoder)

INDEXES = {
    "bo_general" : {
       "csv_fname": "input_ewts_categories.csv",
       "value_to_tokens_fun": ewts_tokenize_to_bo,
       "query_tokenize_fun": bo_tokenize_to_bo,
    },
    "ewts_general": {
        "csv_fname": "input_ewts_categories_kangyur2.csv",
        "value_to_tokens_fun": ewts_tokenize_to_ewts,
        "query_tokenize_fun": ewts_tokenize_to_ewts
    }
}

IDXLOCK = Lock()
def get_index(index_name):
    global IDXLOCK
    if index_name not in INDEXES:
        return None
    with IDXLOCK:
        if index_name in SAVED_INDEXES:
            return SAVED_INDEXES[index_name]
        index_info = INDEXES[index_name]
        pickle_path = index_name+".pickle"
        if Path(pickle_path).is_file():
            logging.info("load index from %s", pickle_path)
            with open(pickle_path, 'rb') as handle:
                index = pickle.load(handle)
                index.query_tokenize_fun = index_info["query_tokenize_fun"]
                SAVED_INDEXES[index_name] = index
                return index
        index = index_from_csv(index_info["csv_fname"], index_info["value_to_tokens_fun"])
        with open(pickle_path, 'wb') as handle:
            pickle.dump(index, handle, protocol=pickle.HIGHEST_PROTOCOL)
        index.query_tokenize_fun = index_info["query_tokenize_fun"]
        SAVED_INDEXES[index_name] = index
        return index

def preload_indexes():
    get_index("ewts_general")
    get_index("bo_general")