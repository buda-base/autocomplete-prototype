import os, re, json, requests
from ssl import create_default_context
import pyewts

# Configuration for the OpenSearch endpoint
os_host = 'https://opensearch.bdrc.io'
auth = (os.getenv('OPENSEARCH_USER'), os.getenv('OPENSEARCH_PASSWORD'))
headers = {'Content-Type': 'application/json'}

def create_mappings(index_name='autosuggest'):
    # Delete the index if it exists
    try:
        response = requests.delete(f"{os_host}/{index_name}", auth=auth, headers=headers, verify=True)
        if response.status_code == 200:
            print(f"Deleted index: {index_name}")
        else:
            print(f"Index {index_name} not found. Proceeding to create it.")
    except Exception as e:
        print(str(e))

    # Recreate the index with the specified mappings
    mappings = {
        "mappings": {
            "properties": {
                "typed": {
                    "type": "keyword"
                },
                "suggestion": {
                    "type": "text",
                    "index": False
                },
                "length": {
                    "type": "integer",
                    "index": False
                },
                "priority": {
                    "type": "integer"
                }
            }
        }
    }
    response = requests.put(f"{os_host}/{index_name}", auth=auth, headers=headers, json=mappings, verify=True)
    if response.status_code == 200:
        print(f"Created index: {index_name}")
    else:
        print("Failed to create index")

def reindex():
    converter = pyewts.pyewts()
    doubles = {}
    ten_max = {}
    data = []
    progress = 0
    with open('input_ewts_categories.csv', 'r') as file:
        for line in file:
            try:
                suggestion, priority, dummy = re.findall('"(.*?)"', line) # dummy because the CSV still has "category" although removed from index
            except:
                #print(f'Cannot read: {line}')
                continue
            suggestion = re.sub('/$', '', suggestion)
            if suggestion in doubles:
                continue
            doubles[suggestion] = 1
            data.append({'suggestion': suggestion, 'priority': priority})
    put = []

    for line in sorted(data, key=lambda x: int(x['priority']), reverse=True):
        progress += 1
        for length in range(1, len(line['suggestion']) + 1):
            if ((length > 21 and length % 2 == 0)  or length > 40) and length < len(line['suggestion']):
                continue
            prefix = line['suggestion'][:length]
            if prefix in ten_max:
                if ten_max[prefix] > 10:
                    continue
                else:
                    ten_max[prefix] += 1
            else:
                ten_max[prefix] = 1
            put.append({'index': {'_index': 'autosuggest'}})
            put.append({'typed': prefix, 'suggestion': line['suggestion'], 'length': length, 'priority': line['priority']})
            if len(put) >= 5000:
                response = requests.post(f"{os_host}/_bulk", auth=auth, headers={'Content-Type': 'application/x-ndjson'}, data='\n'.join(json.dumps(p) for p in put) + '\n', verify=True)
                if response.status_code != 200:
                    print(f"Failed bulk request: {response.text}   {response.status_code}")
                    #input(put)
                    break
                #print('\r' + str(int(100 * progress/len(data)) + 1) + '%', end='')
                print(str(int(100 * progress/len(data)) + 1) + '%')
                put = []
    if put:
        response = requests.post(f"{os_host}/_bulk", auth=auth, headers={'Content-Type': 'application/x-ndjson'}, data='\n'.join(json.dumps(p) for p in put) + '\n', verify=True)
        if response.status_code != 200:
            print(f"Failed final bulk request: {response.text}")

create_mappings()
reindex()
