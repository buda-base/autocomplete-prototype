import os, json, re, time
import requests
from requests.auth import HTTPBasicAuth
from uniseg.wordbreak import word_breakables

index_json = '/Users/roopekoski/Documents/Firma/BDRC/code/get-index-os/index.json'

MAX_INPUT_LENGTH = 100
CUT_AFTER = 50

def create_mappings():
    url = os.getenv('OPENSEARCH_URL') + INDEX_NAME
    # Delete index
    response = requests.delete(url, auth=HTTPBasicAuth(os.getenv('OPENSEARCH_USER'), os.getenv('OPENSEARCH_PASSWORD')))
    if response.status_code != 200:
        print(f"Failed to delete the old index: {response.status_code} {response.text}")

    mappings = {
        "mappings": {
            "properties": {
                "suggest_me": {
                    "type": "completion",
                    "max_input_length": MAX_INPUT_LENGTH,
                    "contexts": [
                        {
                            "name": "scope",
                            "type": "category",
                            "path": "scope"
                        }
                    ]
                },
                "scope": {
                    "type": "keyword"
                },
                "lang": {
                    "type": "keyword"
                },         
                "id": {
                    "type": "keyword"
                }         
            }
        }
    }
    response = requests.put(url, json=mappings, auth=HTTPBasicAuth(user, password))
    if response.status_code != 200:
        exit(f"Failed to create mappings: {response.status_code} {response.text}")
    else:
        print('Created mappings.')

# all ranking scores for autosuggest are calculated here.  nothing is calculated at query time.
# it is good to calculate this in the same way as in the script_score in the normal search
def get_weight(data):
    score = 0.5
    # page type
    if 'type' in data:
        entity_type = data['type'][0]
        if entity_type == 'Instance':
            score *= 1
        elif entity_type == 'Person':
            score *= 0.9
        elif entity_type == 'Topic':
            score *= 0.8
        elif entity_type == 'PartTypeText':
            score *= 0.75
        elif entity_type == 'PartTypeVolume':
            score *= 0.6
        elif entity_type == 'PartTypeCodicologicalVolume':
            score *= 0.6
        elif entity_type == 'PartTypeChapter':
            score *= 0.55
        elif entity_type == 'PartTypeSection':
            score *= 0.55
        elif entity_type == 'Collection':
            score *= 0.5
        elif entity_type == 'Place':
            score *= 0.4
        elif entity_type == 'PartTypeEditorial':
            score *= 0.01
        elif entity_type == 'PartTypeTableOfContent':
            score *= 0.01
        else:
            exit('"type" missing from ' + json.dumps(data))
    
    # access levels
    scans_access = data.get('scans_access', 3)
    etext_access = data.get('etext_access', 1)
    if scans_access == 5 and etext_access == 3:
        access = 1.0
    elif scans_access == 5:
        access = 0.99
    elif scans_access == 4 and etext_access == 3:
        access = 1.0
    elif scans_access == 4:
        access = 0.8
    elif scans_access == 3 and etext_access == 3:
        access = 0.9
    elif scans_access == 3 and etext_access == 2:
        access = 0.55
    elif scans_access == 3:
        access = 0.5
    elif scans_access == 2 and etext_access == 3:
        access = 0.85
    elif scans_access == 2:
        access = 0.4
    elif scans_access == 1 and etext_access == 3:
        access = 0.75
    elif scans_access == 1 and etext_access == 2:
        access = 0.35
    elif scans_access == 1 and etext_access == 1:
        access = 0.25

    score *= access

    # popularity and db scores
    score *= data.get('pop_score', 0.4) - 0.3
    score *= data.get('db_score', 0.5) - 0.05 # boost db score less

    # etext quality todo
    # freshness todo

    return int(score * 10000000)

def normalize_label(label):
    """
    label normalization before sending to index
    """
    label = re.sub("[‘’‛′‵ʼʻˈˊˋ`]", "'", label)
    return label

def find_word_positions(s):
    """
    returns a tuple (cstart, cend) for each word in the sentence, Unicode-aware.

    For instance on "Hello, 世界! This 'is a' test." it will return [(0, 5), (7, 8), (8, 9), (11, 15), (16, 18), (19, 20), (21, 25)]
    corresponding to:

    (0, 5): Hello
    (7, 8): 世
    (8, 9): 界
    (11, 15): This
    (16, 18): is
    (19, 20): a
    (21, 25): test
    """
    # Pattern to match groups of Unicode word characters + single quote (which we assume represents a letter in Wylie)
    word_char_groups = re.finditer(r"('|\w)+", s, re.UNICODE)
    word_breaks = list(word_breakables(s))
    # returns a list with the same length as s that contains every word breaking
    # opportunity, 0 for no break, 1 for break
    
    positions = []
    
    for match in word_char_groups:
        start = match.start()
        end = match.end()
        
        # Use uniseg's word_breakables to find word boundaries within Unicode word character groups
        current_position = start
        for i in range(start, end):
            # Check if a break is possible at this position
            if word_breaks[i] == 1 and s[i] != "'" and (i == 0 or s[i-1] != "'"):
                # If a break is possible, add the word from current_position to i
                if current_position != i:
                    positions.append((current_position, i))
                current_position = i
        
        # Append the last word segment if any
        if current_position != end:
            positions.append((current_position, end))

    return positions

def print_word_positions(s, positions):
    """
    Simple print function to debug positions
    """
    for (cstart, cend) in positions:
        print("(%d, %d): %s" % (cstart, cend, s[cstart:cend]))

#print_word_positions("Hello, 世界! This 'is a' test'.", find_word_positions("Hello, 世界! This 'is a' test"))

def cut_positions_after(positions, cnum):
    """
    given a list of character positions (cstart, cend), return a new
    list with only the positions before a certain character
    """
    if len(positions) == 0 or positions[-1][1] < cnum:
        return positions

    res = []
    for position in positions:
        if position[1] < cnum:
            res.append(position)
        else:
            return res
    return res

# create variations to begin suggestions at any token
def suggest_me_variations(label_list, weight):
    variations = []
    for label in label_list:
        # remove shads from end and harmonise apostrophes
        label = normalize_label(label)
        token_positions = find_word_positions(label)
        length = len(token_positions)
        if length == 0:
            return []
        if length > 2:
            # first we cut all the tokens after character 256:
            token_positions = cut_positions_after(token_positions, 256)
            # then we add the partial tokens
            for token_position_i in range(0, len(token_positions) - 1):
                # we take all the positions between the current token and current token + 12 (or the end)
                last_token_position_i = min(len(token_positions), token_position_i+12)
                variant_positions = token_positions[token_position_i:last_token_position_i]
                # we don't want suggestions of more than CUT_AFTER characters
                # first calculate character coordinate to cut after for this variant:
                variant_cut_after = positions[token_position_i][0] + CUT_AFTER
                # we cut the list so that we don't have suggestions of more than CUT_AFTER characters
                variant_positions = cut_positions_after(variant_positions, variant_cut_after)
                # safeguard, shouldn't happen often:
                if len(variant_positions) == 0:
                    continue
                # we take the substring between the first and last position of this variant
                partial_match = label_list[variant_positions[0][0]:variant_positions[-1][1]]
                variations.append({'input': partial_match, 'weight': int(weight * (1 - 0.01 * token_position_i))})
        else:
            # in order to strip punctuation we use the token coordinates:
            variations.append({'input': label[token_positions[0][0]:token_positions[0][1]], 'weight': int(weight)})
        
    return variations

# create json of one page
def one_doc(data, doc_id):
    puts = []
    prefLabels = {}
    altLabels = {}
    scope = ['all']
    weight = get_weight(data['_source'])

    for field, value in data['_source'].items():
        # Create autosuggest variations for prefLabels and altLabels
        if 'Label_' in field:
            lang = re.sub('(pref|alt)Label_', '', field)
            if 'prefLabel_' in field:
                prefLabels[lang] = suggest_me_variations(value, weight)
            elif 'altLabel_' in field:
                altLabels[lang] = suggest_me_variations(value, weight * 0.6)
        # collect IDs for scoped autosuggest
        elif field in ['associatedTradition', 'inRootInstance', 'associated_res']:
            scope += value

    for lang in prefLabels:
        doc_id += 1
        puts += ([
            { "index" : { "_index" : "bdrc_autosuggest", "_id" : doc_id } },
            {'suggest_me': prefLabels[lang], 'scope': scope, 'lang': lang, 'id': data['_id']}
        ])
    for lang in altLabels:
        doc_id += 1
        puts += ([
            { "index" : { "_index" : "bdrc_autosuggest", "_id" : doc_id } },
            {'suggest_me': altLabels[lang], 'scope': scope, 'lang': lang, 'id': data['_id']}
        ])
    
    # combine the json objects in ES format
    puts = '\n'.join(json.dumps(p) for p in puts)  + '\n'
    return puts, doc_id

# read fron index.json in which each line is a json for one doc
def index_labels():
    doc_id = 0
    puts = []
    batch = ''
    with open(index_json) as file:
        for line in file:
            data = json.loads(line)
            add_to_batch, doc_id = one_doc(data, doc_id)

            #input(json.dumps(add_to_batch, indent=4))

            batch += add_to_batch
            if len(batch) > batch_size:
                if doc_id < start_at_doc:
                    batch = ''
                    print(doc_id, 'Skip')
                    continue
                send_batch(batch)
                batch = ''
                print(doc_id)



def send_batch(batch):
    headers = {"Content-Type": "application/json"}
    url = os.getenv('OPENSEARCH_URL') + INDEX_NAME
    response = requests.post(url + '/_bulk', headers=headers, data=batch, auth=HTTPBasicAuth(user, password))

    # Try again after unauthorized.
    if response.status_code != 200:
        if response.status_code == 413:
            print('Batch too big begin')
            print(batch)
            print('Batch too big end')
            return
        else:
            success = False
            for retry in range(1, 6):
                time.sleep(retry)
                print(f'Status code: {response.status_code}: Trying again {retry}/5')
                response = requests.post(url + '/_bulk', headers=headers, data=batch, auth=HTTPBasicAuth(user, password))
                if response.status_code == 200:
                    print(f'Problem solved: {response.status_code}')
                    success = True
                    break
            if not success:
                print(batch)
                exit(f"Batch index failed: {response.status_code} {response.text}")

start_at_doc = 0
batch_size = 900000

if __name__ == "__main__":
    if not start_at_doc:
        create_mappings()
    index_labels()