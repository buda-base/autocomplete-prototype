import os, re, json
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from opensearchpy.exceptions import NotFoundError
from ssl import create_default_context
import pyewts


def create_mappings(index_name='autosuggest'):
    # Delete the index if it exists
    try:
        os_client.indices.delete(index=index_name)
        print(f"Deleted index: {index_name}")
    except NotFoundError:
        print(f"Index {index_name} not found. Proceeding to create it.")
    
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
                },
                "category": {
                    "type": "text",
                    "index": False
                }
            }
        }
    }
    
    os_client.indices.create(index=index_name, body=mappings)
    print(f"Created index: {index_name}")

def reindex():
    count = 1
    progress = 0
    converter = pyewts.pyewts()
    doubles = {}
    ten_max = {}
    data = []
    with open('input_ewts_categories.csv', 'r') as file:
        for line in file:
            try: suggestion, priority, category = re.findall('"(.*?)"', line)
            except: print(f'Cannot read: {line}')
            suggestion = re.sub('/$', '', suggestion)
            if suggestion + category in doubles:
                continue
            doubles[suggestion + category] = 1
            data.append({'suggestion': suggestion, 'priority': priority, 'category': category})

    put = []
    for line in sorted(data, key=lambda x: int(x['priority']), reverse=True):
        doubles[line['suggestion']] = 1
        for length in range(1, len(line['suggestion']) + 1):
            if length > 21 and length % 2 == 0 and length < len(line['suggestion']):
                continue
            # index only ten same prefixes with highest priorities, because the rest will be never shown
            prefix = line['suggestion'][:length]
            if prefix in ten_max:
                if ten_max[prefix] > 10:
                    continue
                else:
                    ten_max[prefix] += 1
            else:
                ten_max[prefix] = 1

            #[{"category":"Person","lang":"bo-x-ewts","res":"byam<suggested>s chen chos rje shAkya ye shes/</suggested>"},{"category":"Person","lang":"bo-x-ewts","res":"byam<suggested>s pa bsod nams dbang po/</suggested>"}]
            put.append({'_index': 'autosuggest', '_source': {'typed': prefix, 'suggestion': line['suggestion'], 'length': length, 'priority': line['priority'], 'category': line['category']}})
            count += 1
            if count == 20000:
                response = bulk(os_client, put)
                put = []
                print(f'\r{int(100 * progress / len(data)) + 1}%', end='')
                count = 0
        progress += 1
    # index the rest
    response = bulk(os_client, put)

# for demo purposes, SSL is disabled by starting the container with DISABLE_SECURITY_PLUGIN=true
# docker run -it -p 9200:9200 -p 9600:9600 -e OPENSEARCH_INITIAL_ADMIN_PASSWORD="bdrcBDRC/0" -e "discovery.type=single-node" -e DISABLE_SECURITY_PLUGIN=true  --name opensearch-node opensearchproject/opensearch:latest
os_client = OpenSearch(
    [{'host': 'localhost', 'port': 9200}],
    basic_auth=('admin', os.getenv('OPENSEARCH_PW')),
    use_ssl=False,
    verify_certs=False
)


create_mappings()
reindex()

