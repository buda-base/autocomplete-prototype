from flask import Flask, request
from flask_cors import CORS
import re, json, requests
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes

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

    if fuzzy:
        search_body['query']['bool']['must_not'] = {'match': {'typed': keyword}}

    headers = {'Content-Type': 'application/json'}
    auth = (os.environ['OPENSEARCH_USER'], os.environ['OPENSEARCH_PASSWORD'])
    url = os.environ['OPENSEARCH_URL']+'/autosuggest/_search'
    response = requests.post(url, headers=headers, auth=auth, json=search_body, timeout=1, verify=False)
    return response.json()['hits']['hits']

@app.route('/autosuggest', methods=['POST'])
def autosuggest():
    data = request.json
    print(data)
    keyword = data['query']

    keyword = keyword.lower()

    if re.search(r'[\u0F00-\u0FFF]', keyword):
        from pyewts import pyewts
        converter = pyewts()
        keyword = converter.toWylie(keyword)
        keyword = re.sub(r'(\S)a$', r'\1', keyword)
        is_tibetan = 1
    else:
        is_tibetan = 0

    response = do_search(keyword, fuzzy=0)
    if len(response) < 10:
        response += do_search(keyword, fuzzy=1)

    result = []
    for hit in response[:10]:
        category = hit['_source'].get('category', '')
        if is_tibetan:
            lang = 'bo'
            suggestion = converter.toUnicode(hit['_source']['suggestion'])
        else:
            lang = 'bo-x-ewts'
            match = '?.?'.join(x for x in keyword)
            suggestion = re.sub(f'^(.{match})(.*)$', r'\1<suggested>\2</suggested>', hit['_source']['suggestion'])
        result.append({'category': category, 'lang': lang, 'res': suggestion})

    print(json.dumps(result, indent=4))
    return json.dumps(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
