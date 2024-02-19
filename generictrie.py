import csv

# Simple decorated Trie with helper functions

## inspired from https://gist.github.com/nickstanisha/733c134a0171a00f66d4

class Node:
    def __init__(self, label=None, score=-1, category=None, canbefinal=True):
        self.label = label
        self.scores = None
        self.children = {}
        self.top_10 = {}
        self.min_top_10_idx = 0
    
    def addChild(self, key, score, canbefinal=True):
        child_label = None
        if not isinstance(key, Node):
            self.children[key] = Node(key, score, canbefinal)
            child_label = key
        else:
            self.children[key.label] = key
            child_label = key.label
        if score > self.min_top_10_score:
            for i, score in enumerate(self.top_10.keys()):
                if score == self.min_top_10_score:
                    del self.top_10[score]
            self.min_top_10_score = score
            self.top_10[score] = child_label

    def set_score_in_category(self, score, category):
        if self.scores is None:
            self.scores = {}
        self.scores[category] = score

    def __getitem__(self, key):
        return self.children[key]

class Trie:
    def __init__(self):
        self.head = Node()
    
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
        if self.scores is not None:
            for cat, score in self.scores:
                if score >= score_limit:
                    res.append((cur_suffix, cat, score))
        if len(res) >= 10:
            return
        child_l_to_lowest_score_to_explore = {}
        for score, child_l in node.top_10.items():
            if score >= score_limit:
                if child_l not in lowest_score_to_node:
                    child_l_to_lowest_score_to_explore[child_l] = score
                else:
                    child_l_to_lowest_score_to_explore[child_l] = min(score, child_l_to_lowest_score_to_explore[child_l])
        for c_l, score in children_with_high_score:
            self.get_top_10_suffixes_for_node(res, node.children[c_l], cur_suffix+c_l, score)
    
    def get_top_10_suffixes(self, word, score_limit=0):
        current_node = self.head
        for c in word:
            if c in current_node.children:
                current_node = current_node.children[c]
            else:
                return None
        res = []
        self.get_top_10_suffixes_for_node(res, current_node, "", score_limit)
        return res


if __name__ == '__main__':
    """ Example use """
    trie = Trie()
    trie.add("test", "test_data")
    trie.add("t", "t_data")
    print(trie.get_longest_match_with_data("test"))
    print(trie.get_data("test"))
    print(trie.get_longest_match_with_data("tes"))
    trie.add("te", "te_data", False)
    print(trie.get_longest_match_with_data("tes"))
    print(trie.get_longest_match_with_data("te"))
    def iteratortest(word, data):
        print("data for \""+word+"\": "+data)
    trie.walk_all_data(iteratortest)
