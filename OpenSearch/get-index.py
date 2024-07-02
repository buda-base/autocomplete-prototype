from opensearchpy import OpenSearch
import re, json, os

# Connect to OpenSearch
client = OpenSearch(
    hosts=[{'host': 'opensearch.bdrc.io', 'port': 443}],
    http_auth=(os.environ['OPENSEARCH_USER'], os.environ['OPENSEARCH_PASSWORD']),
    use_ssl=True,
    verify_certs=True
)

# Define the scroll size and duration
scroll_size = 1000
scroll_duration = '2m'

# Initialize the scroll
response = client.search(
    index='bdrc_prod',
    scroll=scroll_duration,
    size=scroll_size,
    body={
        "query": {
            "match_all": {}
        }
    }
)

# Retrieve the scroll ID and the first batch of documents
scroll_id = response['_scroll_id']

# Iterate through the scroll
while len(response['hits']['hits']):
    for doc in response['hits']['hits']:
        print(json.dumps(doc))
    response = client.scroll(
        scroll_id=scroll_id,
        scroll=scroll_duration
    )
    scroll_id = response['_scroll_id']
