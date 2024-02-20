import csv
import logging

#logging.basicConfig(level=logging.DEBUG)

# Simple decorated Trie with helper functions

## inspired from https://gist.github.com/nickstanisha/733c134a0171a00f66d4

class Node:
    def __init__(self, label=None, score=-1, category=None, canbefinal=True):
        self.label = label
        self.scores = None
        self.children = {}
        self.top_10_scores = []
        self.top_10_children = []
        self.min_top_10_score = -1
    
    def addChild(self, key, score, canbefinal=True):
        child_label = None
        if not isinstance(key, Node):
            self.children[key] = Node(key, score, canbefinal)
            child_label = key
        else:
            self.children[key.label] = key
            child_label = key.label
        if score > self.min_top_10_score:
            if len(self.top_10_scores) > 9:
                idx_to_replace = -1
                for i, score in enumerate(self.top_10_scores):
                    if score == self.min_top_10_score:
                        idx_to_replace = i
                        break
                self.top_10_scores[idx_to_replace] = score
                self.top_10_children[idx_to_replace] = child_label
            else:
                self.top_10_scores.append(score)
                self.top_10_children.append(child_label)
            self.min_top_10_score = min(self.top_10_scores)

    def set_score_in_category(self, score, category):
        if self.scores is None:
            self.scores = {}
        self.scores[category] = score

    def __getitem__(self, key):
        return self.children[key]

    def debug(self, encoder):
        child_to_decoded = {}
        for c in self.children:
            child_to_decoded[c] = c if encoder is None else encoder.decode(ord(c))
        label = self.label if encoder is None else encoder.decode(ord(self.label))
        res =  "Node: %s children %s" % (label, str(list(child_to_decoded.values())))
        children_in_top_10 = []
        for c in self.top_10_children:
            children_in_top_10.append(child_to_decoded[c])
        res += "   top_10 children: %s" % str(children_in_top_10)
        res += "   scores: %s" % str(self.scores)
        return res


class Trie:
    def __init__(self, encoder=None):
        self.head = Node()
        self.encoder = encoder
    
    def __getitem__(self, key):
        return self.head.children[key]
    
    def add(self, s, score, category, canbefinal=True):
        current_node = self.head
        for c in s:
            if c not in current_node.children:
                current_node.addChild(c, score)
            current_node = current_node.children[c]
        current_node.set_score_in_category(score, category)

    def get_top_10_suffixes_for_node(self, res, node, cur_suffix="", score_limit=0):
        #logging.debug("get top 10 suffixes for %s (score limit %d)" % (node.debug(self.encoder), score_limit))
        if node.scores is not None:
            for cat, score in node.scores.items():
                if score >= score_limit:
                    res.append((cur_suffix, cat, score))
        if len(res) >= 10:
            return
        child_l_to_lowest_score_to_explore = {}
        for i, score in enumerate(node.top_10_scores):
            if score >= score_limit:
                child_l = node.top_10_children[i]
                if child_l not in child_l_to_lowest_score_to_explore:
                    child_l_to_lowest_score_to_explore[child_l] = score
                else:
                    child_l_to_lowest_score_to_explore[child_l] = min(score, child_l_to_lowest_score_to_explore[child_l])
        for c_l, score in child_l_to_lowest_score_to_explore.items():
            self.get_top_10_suffixes_for_node(res, node.children[c_l], cur_suffix+c_l, score)
    
    def get_top_10_suffixes(self, word, possible_last_tokens, score_limit=0):
        current_node = self.head
        for c in word:
            if c in current_node.children:
                current_node = current_node.children[c]
            else:
                return None
        res = []
        if not possible_last_tokens:
            self.get_top_10_suffixes_for_node(res, current_node, "", score_limit)
        else:
            for plt in possible_last_tokens:
                if plt not in current_node.children:
                    continue
                potential_child_node = current_node.children[plt]
                self.get_top_10_suffixes_for_node(res, current_node, "", score_limit)
                if res:
                    score_limit = max(score_limit, res[-1].score)
        return res[:10]