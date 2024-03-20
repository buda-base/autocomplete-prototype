from flask import Flask, request
from flask_cors import CORS
import re, json, os
from opensearchpy import OpenSearch

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes


# for demo purposes, SSL is disabled by starting the container with DISABLE_SECURITY_PLUGIN=true
# docker run -it -p 9200:9200 -p 9600:9600 -e OPENSEARCH_INITIAL_ADMIN_PASSWORD="bdrcBDRC/0" -e "discovery.type=single-node" -e DISABLE_SECURITY_PLUGIN=true  --name opensearch-node opensearchproject/opensearch:latest
os_client = OpenSearch(
    [{'host': 'localhost', 'port': 9200}],
    http_auth=('admin', os.getenv('OPENSEARCH_PW')),
    use_ssl=False,
    verify_certs=False
)

def do_search(keyword, fuzzy):
    length = len(keyword)
    if fuzzy:
        if length < 3:
            fuzziness = 0
        elif length < 8:
            fuzziness = 1
        else:
            fuzziness = 2
    else:
        fuzziness = 0

    search_body = {
        'query': {
            'bool': {
                'must': {
                    'match': {
                        'typed': {
                            'query': keyword,
                            'fuzziness': fuzziness,
                            'prefix_length': 0
                        }
                    }
                },
                'filter': {
                    'term': {'length': length}
                }
            }
        },
        'sort': [
            {
                'priority': {
                    'order': 'desc'
                }
            }
        ]
    }

    # do not return exact matches in fuzzy search, because they have been returned in non-fuzzy search
    if fuzzy:
        search_body['query']['bool']['must_not'] = {'match': {'typed': keyword}}

    response = os_client.search(index='autosuggest', body=search_body, _source=['suggestion', 'category'])
    return response['hits']['hits']

@app.route('/autosuggest', methods=['POST'])
def autosuggest():
    data = request.json
    print(data)
    keyword = data['query']

    keyword = keyword.lower()

    # tibetan unicode
    is_tibetan = 0
    if re.search(r'[\u0F00-\u0FFF]', keyword):
        from pyewts import pyewts
        converter = pyewts()
        keyword = converter.toWylie(keyword)
        keyword = re.sub('(\S)a$', r'\1', keyword)
        is_tibetan = 1

    # non-fuzzy search
    response = do_search(keyword, fuzzy=0)
    # fuzzy search
    if len(response) < 10:
        response += do_search(keyword, fuzzy=1)


    # format output
    result = []
    for hit in response[:10]:
        if 'category' not in hit['_source']:
            hit['_source']['category'] = ''
        if is_tibetan:
            lang = 'bo'
            res = converter.toUnicode(hit['_source']['suggestion'])
        else:
            lang = 'bo-x-ewts'
            # imitate fuzzy match in regex to highlight fuzzy results
            match = '?.?'.join(x for x in keyword)
            res = re.sub(f'^(.{match})(.*)$', r'\1<suggested>\2</suggested>', hit['_source']['suggestion'])
        result.append({'category':hit['_source']['category'], 'lang': lang, 'res': res})

    print(json.dumps(result, indent=4))

    return result

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    #print(do_search('mdo', 0))
