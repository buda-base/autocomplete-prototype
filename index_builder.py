import pickle
from encoder import Encoder
from generictrie import Trie
import logging
from pathlib import Path
import csv
import pyewts
from utils import normalize_bo, tokenize_bo
from botok import tokenize_in_stacks
import sys

sys.setrecursionlimit(10000)

EWTSCONVERTER = pyewts.pyewts()

SAVED_INDEXES = {}

class Index:
    def __init__(self, trie, encoder, partial_to_full, cat_encoder):
        self.trie = trie
        self.encoder = encoder
        self.partial_to_full = partial_to_full
        self.cat_encoder = cat_encoder

def index_from_csv(csv_fname):
    logging.info("build index from %s", csv_fname)
    encoder = Encoder(allow_decode=True)
    cat_encoder = Encoder(allow_decode=True)
    partial_to_full = {}
    trie = Trie(encoder)
    with open(csv_fname, newline='') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            s = EWTSCONVERTER.toUnicode(row[0])
            s = normalize_bo(s)
            score = int(row[1])
            encoded_cat = cat_encoder.encode(row[2])
            token_list = tokenize_in_stacks(s)
            encoded_token_list = ""
            for t in token_list:
                encoded_t = encoder.encode(t)
                encoded_token_list += chr(encoded_t)
                # fill partial_to_full
                for i in range(1, len(t)):
                    partial = t[:i]
                    if partial not in partial_to_full:
                        partial_to_full[partial] = set()
                    partial_to_full[partial].add(chr(encoded_t))
            trie.add(encoded_token_list, score, encoded_cat)
    return Index(trie, encoder, partial_to_full, cat_encoder)

def get_index(index_name):
    if index_name in SAVED_INDEXES:
        return SAVED_INDEXES[index_name]
    pickle_path = index_name+".pickle"
    if Path(pickle_path).is_file():
        logging.info("load index from %s", pickle_path)
        with open(pickle_path, 'rb') as handle:
            index = pickle.load(handle)
            SAVED_INDEXES[index_name] = index
            return index
    fname = "input_ewts_categories.csv"
    index = index_from_csv(fname)
    with open(pickle_path, 'wb') as handle:
        pickle.dump(index, handle, protocol=pickle.HIGHEST_PROTOCOL)
    SAVED_INDEXES[index_name] = index
    return index
