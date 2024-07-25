import os, json, re, time
import requests
from requests.auth import HTTPBasicAuth

url = os.getenv('OPENSEARCH_URL') + '/bdrc_autosuggest'
user = os.getenv('OPENSEARCH_USER')
password = os.getenv('OPENSEARCH_PASSWORD')
index_json = '/Users/roopekoski/Documents/Firma/BDRC/code/get-index-os/index.json'

def create_mappings():
    # Delete index
    response = requests.delete(url, auth=HTTPBasicAuth(user, password))
    if response.status_code != 200:
        print(f"Failed to delete the old index: {response.status_code} {response.text}")

    mappings = {
        "mappings": {
            "properties": {
                "suggest_me": {
                    "type": "completion",
                    "max_input_length": 100,
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

# create variations to begin suggestions at any token
def suggest_me_variations(label_list, weight):
    variations = []
    for label in label_list:
        # remove shads from end and harmonise apostrophes
        label = re.sub('/$', '', label.strip())
        label = re.sub("[‘’‛′‵ʼʻˈˊˋ`]", "'", label)
        label = label[:256]
        tokens = re.split('\s+', label)
        length = len(tokens)
        if length > 2:
            for i in range(0, len(tokens) - 1):
                partial_match = ' '.join(tokens[i: i+12])
                variations.append({'input': partial_match, 'weight': int(weight * (1 - 0.01 * i))})
        else:
            variations.append({'input': label, 'weight': int(weight)})
        
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


if url == None or user == None or password == None:
    exit('Need env variables OPENSEARCH_URL, OPENSEARCH_USER and OPENSEARCH_PASSWORD')



start_at_doc = 0
batch_size = 900000

if not start_at_doc:
    create_mappings()
index_labels()

