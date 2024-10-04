import os, json, re, time
import requests
from requests.auth import HTTPBasicAuth
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from pre_phonetix import *

URL = os.getenv('OPENSEARCH_URL')
USER = os.getenv('OPENSEARCH_USER')
PASSWORD = os.getenv('OPENSEARCH_PASSWORD')

def prepare_batch(prod_json):
    batch = []
    # loop through docs from bdrc_prod
    for doc in prod_json['hits']['hits']:
        prefs = []
        alts = []

        for wylie in doc['_source'].get('prefLabel_bo_x_ewts', []):
            prephon = convert_to_fonetix(wylie_to_phonetics(wylie))
            prephon = re.sub('[^a-z0-9 ]', '', prephon.strip())
            prefs.append(prephon)
        for wylie in doc['_source'].get('altLabel_bo_x_ewts', []):
            prephon = convert_to_fonetix(wylie_to_phonetics(wylie))
            prephon = re.sub('[^a-z0-9 ]', '', prephon.strip())
            alts.append(prephon)

        doc_value = {}
        if prefs:
            batch.append({ "update": { "_id": doc['_id'] } })
            doc_value["prefLabel_prePhon"] = prefs
            if alts:
                doc_value["altLabel_prePhon"] = prefs
            batch.append({ "doc": doc_value })

    batch_ndjson = '\n'.join(json.dumps(d) for d in batch) + '\n'
    return batch_ndjson

def index_pre_phonetics():
    scroll_size = 10000

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
        },
        "_source": ["prefLabel_bo_x_ewts", "altLabel_bo_x_ewts"]
    }

    auth = HTTPBasicAuth(USER, PASSWORD)

    r = requests.post(search_url, json=search_body, auth=auth, verify=False)
    if r.status_code != 200:
        print('Error from Opensearch:', r.status_code, r.text)
        exit()
    response = r.json()

    # Iterate through the scroll
    count = 1
    while True:
        # stop when no more results in the scroll
        if not len(response['hits']['hits']):
            print('Done')
            break

        scroll_id = response['_scroll_id']

        # process the data from bdrc_prod and send it to bdrc_autosuggest
        batch = prepare_batch(response)

        send_batch(batch)

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

        print(count)
        count += 1

def send_batch(batch):
    if not re.search('\S', batch):
        return
    headers = {"Content-Type": "application/json"}
    response = requests.post(URL  + '/bdrc_prod/_bulk', headers=headers, data=batch, auth=HTTPBasicAuth(USER, PASSWORD))
    # Try again after unauthorized.
    if response.status_code != 200:
        input('Batch put failed' + response.text)
        input(batch)

if URL == None or USER == None or PASSWORD == None:
    exit('Need env variables OPENSEARCH_URL, OPENSEARCH_USER and OPENSEARCH_PASSWORD')

index_pre_phonetics()

