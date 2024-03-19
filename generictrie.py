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
        if category in self.scores:
            self.scores[category] = max(score, self.scores[category])
        else:    
            self.scores[category] = score

    def get_max_score(self, include_children=True):
        res = 0
        if self.scores:
            res = max(self.scores.values())
        if include_children and self.top_10_scores:
            res_children = max(self.top_10_scores)
            res = max(res, res_children)
        return res

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

    def get_top_10_suffixes_for_node(self, res, node, prefix, lev_dst, cur_suffix="", score_limit=0):
        logging.debug("get top 10 suffixes for %s (score limit %d)" % (node.debug(self.encoder), score_limit))
        if node.scores is not None:
            for cat, score in node.scores.items():
                if score >= score_limit:
                    res.append((cur_suffix, cat, score, prefix, lev_dst))
                    res.sort(key=lambda x: x[2], reverse=True)
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
            self.get_top_10_suffixes_for_node(res, node.children[c_l], prefix, lev_dst, cur_suffix+c_l, score)
    
    def get_top_10_nodes_with_lvs_dst_for_node(self, res, node, word, part, lvs_row, lev_dst):
        # if we reached the query string, return
        if part == word:
            return

        max_node_score = node.get_max_score()
        lowest_res_score = 0 if res == [] else res[-1][2]

        if len(res) >= 10 and max_node_score < lowest_res_score:
            return

        if lvs_row[-1] == lev_dst:
            res.append((node, part, max_node_score))
            res.sort(key=lambda x: x[2], reverse=True)
            if len(res) > 10:
                del res[-1]
            return

        # Explore all possible next characters from the current Trie node.
        for char in node.children:
            # Compute the next row of the distance matrix for the current character.
            # The first value is always the row number, representing the cost of deleting characters
            # from the query to match the current part.
            next_row = [lvs_row[0] + 1]
            for col in range(1, len(lvs_row)):
                insert_cost = lvs_row[col] + 1  # Cost to insert a character into the query.
                delete_cost = next_row[col - 1] + 1  # Cost to delete a character from the current part.
                replace_cost = lvs_row[col - 1] + (word[col - 1] != char)  # Cost to replace a character.
                next_row.append(min(insert_cost, delete_cost, replace_cost))

            # If the minimum value in the next row is within the maximum Levenshtein distance,
            # it means there's still a chance to find a match along this path.
            # Continue the search with this character added to the current part.
            if min(next_row) <= lev_dst:
                self.get_top_10_nodes_with_lvs_dst_for_node(res, node.children[char], word, part + char, next_row, lev_dst)

    def get_top_10_suffixes_for_node_combine(self, res, node, word, lev_dst, possible_last_tokens, score_limit=0):
        if not possible_last_tokens:
            self.get_top_10_suffixes_for_node(res, current_node, word, lev_dst, "", score_limit)
        else:
            for plt in possible_last_tokens:
                if plt not in node.children:
                    continue
                potential_child_node = node.children[plt]
                self.get_top_10_suffixes_for_node(res, node, word, lev_dst, "", score_limit)
                if res:
                    res = sorted(res, key=lambda x: x[2], reverse=True)
                    score_limit = max(score_limit, res[-1][2])
        return res[:10]

    def get_top_10_nodes_with_lvs_dst(self, word, lev_dst, score_limit=0):
        # Initialize the first row of the Levenshtein distance matrix.
        # This row represents the distance between an empty string and the prefixes of the query.
        # It is essentially the cost of inserting characters from the query one by one.
        current_row = list(range(len(word) + 1))
        res = []
        # Start the recursive search from the root node with an empty part and the initial row.
        self.get_top_10_nodes_with_lvs_dst_for_node(res, self.head, word, '', current_row, lev_dst)
        return res

    def get_node_simple(self, word):
        current_node = self.head
        for c in word:
            if c in current_node.children:
                current_node = current_node.children[c]
            else:
                logging.debug("could not find the query in the trie (%s not in children)", c)
                return None
        return current_node

    def get_top_10_suffixes(self, word, possible_last_tokens, max_lev_dst=0, score_limit=0):
        res = []
        for lev_dst in range(max_lev_dst+1):
            potential_nodes = []
            if lev_dst == 0:
                node = self.get_node_simple(word)
                if node:
                    potential_nodes.append((node, word, 0))
            else:
                potential_nodes = self.get_top_10_nodes_with_lvs_dst(word, lev_dst)
            logging.debug("%d nodes with lev dst %d", len(potential_nodes), lev_dst)
            for n in potential_nodes:
                node, part, max_score = n
                self.get_top_10_suffixes_for_node_combine(res, node, part, lev_dst, possible_last_tokens)
            if len(res) >= 10:
                return res
        return res