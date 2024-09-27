import os, json, re, time
import requests
from requests.auth import HTTPBasicAuth
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = os.getenv('OPENSEARCH_URL')
USER = os.getenv('OPENSEARCH_USER')
PASSWORD = os.getenv('OPENSEARCH_PASSWORD')
#index_json = '/Users/roopekoski/Documents/Firma/BDRC/code/get-index-os/index.json'

def create_mappings():
    # Delete index
    response = requests.delete(URL + '/bdrc_autosuggest', auth=HTTPBasicAuth(USER, PASSWORD))
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
    response = requests.put(URL  + '/bdrc_autosuggest', json=mappings, auth=HTTPBasicAuth(USER, PASSWORD))
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
'''
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
'''


# convert bdrc_prod output to an autosuggest batch
def prepare_batch(prod_json, doc_id):
    batch = ''
    # loop through docs from bdrc_prod
    for doc in prod_json['hits']['hits']:
        puts = []
        prefLabels = {}
        altLabels = {}
        scope = ['all']
        weight = get_weight(doc['_source'])

        for field, value in doc['_source'].items():
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
                {'suggest_me': prefLabels[lang], 'scope': scope, 'lang': lang, 'id': doc['_id']}
            ])
        for lang in altLabels:
            doc_id += 1
            puts += ([
                { "index" : { "_index" : "bdrc_autosuggest", "_id" : doc_id } },
                {'suggest_me': altLabels[lang], 'scope': scope, 'lang': lang, 'id': doc['_id']}
            ])
        
        if doc_id >= START_AT_DOC:
            batch += '\n'.join(json.dumps(p) for p in puts)  + '\n'

    return batch, doc_id

def index_autosuggest_from_bdrc_prod():
    doc_id = 0
    scroll_size = 1000

    # Initialize the scroll
    search_url = f"{URL}/bdrc_prod/_search?scroll=30s"
    search_body = {
        "size": scroll_size,
        "query": {
            "bool": {
                "must": [
                    {
                        "match_all": {}
                    }
                ],
                "must_not": [
                    {
                        "term": {
                            "type": "Etext"
                        }
                    }
                ]
            }
        }
    }
    auth = HTTPBasicAuth(USER, PASSWORD)

    r = requests.post(search_url, json=search_body, auth=auth, verify=False)
    if r.status_code != 200:
        print('Error from Opensearch:', r.status_code, r.text)
        exit()
    response = r.json()

    # Iterate through the scroll
    while True:
        # stop when no more results in the scroll
        if not len(response['hits']['hits']):
            print('Done')
            break

        print(f'Get from bdrc_prod: {doc_id} -')

        scroll_id = response['_scroll_id']

        # process the data from bdrc_prod and send it to bdrc_autosuggest
        doc_id_begin = doc_id
        batch, doc_id = prepare_batch(response, doc_id)
        if batch:
            print(f'Put to bdrc_autosuggest: {doc_id_begin} - {doc_id}')
            send_batch(batch)
        else:
            print(f'skip until {START_AT_DOC}: {doc_id_begin} - {doc_id}')

        # get the next batch
        scroll_body = {
            "scroll": "30s",
            "scroll_id": scroll_id
        }
        r = requests.post(f"{URL}/_search/scroll", json=scroll_body, auth=auth, verify=False)
        if r.status_code != 200:
            print('Error from Opensearch:', r.status_code, r.text)
            exit()
        response = r.json()

def send_batch(batch):
    headers = {"Content-Type": "application/json"}

    response = requests.post(URL  + '/bdrc_autosuggest/_bulk', headers=headers, data=batch, auth=HTTPBasicAuth(USER, PASSWORD))

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
                print(f'Status code: {response.status_code} {response.text}: Trying again {retry}/5')
                response = requests.post(URL + '/bdrc_autosuggest/_bulk', headers=headers, data=batch, auth=HTTPBasicAuth(USER, PASSWORD))
                if response.status_code == 200:
                    print(f'Problem solved: {response.status_code}')
                    success = True
                    break
            if not success:
                print(batch)
                exit(f"Batch index failed: {response.status_code} {response.text}")


if URL == None or USER == None or PASSWORD == None:
    exit('Need env variables OPENSEARCH_URL, OPENSEARCH_USER and OPENSEARCH_PASSWORD')

START_AT_DOC = 0

if not START_AT_DOC:
    if __name__ == '__main__':
        input('This will delete the old autosuggest and index it again from bdrc_prod. Press Enter.')
    create_mappings()
index_autosuggest_from_bdrc_prod()

