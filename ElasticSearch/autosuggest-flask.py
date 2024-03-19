from flask import Flask, request
from flask_cors import CORS
import re, json, os
from elasticsearch import Elasticsearch

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes

# The connection requires
# 1. the password in env variable
# 2. the certificate in the same dir with this script
# export ELASTIC_PASSWORD=<the password ES gave after installation>
# docker cp es01:/usr/share/elasticsearch/config/certs/http_ca.crt .
# More at https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html
es = Elasticsearch(
    'https://localhost:9200',
    ca_certs='http_ca.crt',
    basic_auth=('elastic', os.getenv('ELASTIC_PASSWORD'))
)

def search_elastic(keyword, fuzzy):
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

    response = es.search(index='autosuggest', body=search_body, _source=['suggestion', 'category'])
    return response['hits']['hits']

@app.route('/<keyword>')
def autosuggest(keyword):
    keyword = keyword.lower()
    # tibetan unicode
    is_tibetan = 0
    if re.search(r'[\u0F00-\u0FFF]', keyword):
        from pyewts import pyewts
        converter = pyewts()
        keyword = converter.toWylie(keyword)
        is_tibetan = 1

    # non-fuzzy search
    response = search_elastic(keyword, fuzzy=0)
    # fuzzy search
    if len(response) < 10:
        response += search_elastic(keyword, fuzzy=1)

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
            res = re.sub(fr'^(.{match})(.*)$', fr'\1<suggested>\2</suggested>', hit['_source']['suggestion'])
        result.append({'category':hit['_source']['category'], 'lang': lang, 'res': res})

    #print(json.dumps(result, indent=4))

    return result

if __name__ == '__main__':
    app.run(debug=True, port=5001)
