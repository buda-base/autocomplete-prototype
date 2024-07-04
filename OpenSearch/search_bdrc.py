import json, re, requests, pyewts
from requests.auth import HTTPBasicAuth
from flask import Flask, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes

def get_fields(structure):
    #fields = {"altLabel_bo_alalc97":0.6, "altLabel_bo_latn_pinyin":0.6, "altLabel_bo_latn_wadegile":0.6, "altLabel_bo_x_ewts":0.6, "altLabel_cmg_mong":0.6, "altLabel_cmg_x_poppe":0.6, "altLabel_de":0.6, "altLabel_en":0.6, "altLabel_ja_alalc97":0.6, "altLabel_ja_x_ndia":0.6, "altLabel_km":0.6, "altLabel_km_x_twktt":0.6, "altLabel_km_x_unspec":0.6, "altLabel_mn":0.6, "altLabel_mn_alalc97":0.6, "altLabel_pi_khmr":0.6, "altLabel_pi_x_iast":0.6, "altLabel_pi_x_twktt":0.6, "altLabel_sa_alalc97":0.6, "altLabel_sa_deva":0.6, "altLabel_sa_x_iast":0.6, "altLabel_sa_x_ndia":0.6, "altLabel_sa_x_rma":0.6, "altLabel_sa_x_trans":0.6, "altLabel_zh_alalc97":0.6, "altLabel_zh_hani":0.6, "altLabel_zh_latn_pinyin":0.6, "altLabel_zh_latn_pinyin_x_ndia":0.6, "altLabel_zh_latn_wadegile":0.6, "associatedTradition":0.05, "author":0.1, "authorshipStatement_bo_x_ewts":0.005, "authorshipStatement_en":0.005, "authorshipStatement_sa_deva":0.005, "authorshipStatement_zh":0.005, "authorshipStatement_zh_alalc97":0.005, "authorshipStatement_zh_hani":0.005, "authorshipStatement_zh_latn_pinyin_x_ndia":0.005, "comment":0.0001, "comment_bo_x_ewts":0.0001, "comment_en":0.0001, "comment_sa_deva":0.0001, "comment_sa_x_iast":0.0001, "comment_zh_hani":0.0001, "comment_zh_latn_pinyin":0.0001, "prefLabel_bo_alalc97":1, "prefLabel_bo_latn_wadegile":1, "prefLabel_bo_x_ewts":1, "prefLabel_de":1, "prefLabel_en":1, "prefLabel_fr":1, "prefLabel_fr_alalc97":1, "prefLabel_fr_x_iast":1, "prefLabel_ja":1, "prefLabel_ja_alalc97":1, "prefLabel_ja_x_ndia":1, "prefLabel_km":1, "prefLabel_km_x_twktt":1, "prefLabel_km_x_unspec":1, "prefLabel_mn":1, "prefLabel_mn_alalc97":1, "prefLabel_pi_khmr":1, "prefLabel_pi_x_iast":1, "prefLabel_pi_x_twktt":1, "prefLabel_ru":1, "prefLabel_ru_alalc97":1, "prefLabel_sa_alalc97":1, "prefLabel_sa_deva":1, "prefLabel_sa_x_iast":1, "prefLabel_sa_x_ndia":1, "prefLabel_sa_x_phon_en_m_tbrc":1, "prefLabel_sa_x_trans":1, "prefLabel_zh_alalc97":1, "prefLabel_zh_hani":1, "prefLabel_zh_latn_pinyin":1, "prefLabel_zh_latn_pinyin_x_ndia":1, "prefLabel_zh_latn_wadegile":1, "publisherLocation_bo_latn_wadegile":0.01, "publisherLocation_bo_x_ewts":0.01, "publisherLocation_en":0.01, "publisherLocation_fr":0.01, "publisherLocation_mn_alalc97":0.01, "publisherLocation_sa_deva":0.01, "publisherLocation_zh_hani":0.01, "publisherLocation_zh_latn_pinyin_x_ndia":0.01, "publisherName_bo_latn_wadegile":0.01, "publisherName_bo_x_ewts":0.01, "publisherName_en":0.01, "publisherName_fr":0.01, "publisherName_sa_deva":0.01, "publisherName_sa_x_iast":0.01, "publisherName_zh_hani":0.01, "publisherName_zh_latn_pinyin_x_ndia":0.01, "seriesName_bo_x_ewts":0.1, "seriesName_en":0.1, "seriesName_res":0.1, "seriesName_zh_hani":0.1, "seriesName_zh_latn_pinyin_x_ndia":0.1, "translator":0.05, "type":0.5, "workGenre":0.02, "workIsAbout":0.01}
    fields = {"altLabel_bo_x_ewts":0.6, "altLabel_en":0.6, "authorshipStatement_bo_x_ewts":0.005, "authorshipStatement_en":0.005, "comment":0.0001, "comment_bo_x_ewts":0.0001, "comment_en":0.0001, "prefLabel_bo_x_ewts":1, "prefLabel_en":1, "publisherLocation_bo_x_ewts":0.01, "publisherLocation_en":0.01, "publisherName_bo_x_ewts":0.01, "publisherName_en":0.01, "seriesName_bo_x_ewts":0.1, "seriesName_en":0.1}

    #fields = {"prefLabel_bo_x_ewts": 1}
    if structure == 'with_weights':
        return [f'{name}^{weight}' for name, weight in fields.items()]
    elif structure == 'for_autosuggest_highlight':
        return {key: {} for key in fields}
    elif structure == 'as_list':
        return fields.keys()

def phrase_match_json(query):
    query_words = re.split('[ /_]+', query)
    weight_fields = get_fields('with_weights')
    phrase_query = {
        "dis_max": {
            "queries": []
        }
    }

    # collect 'queries'
    # 1. full query perfect match
    should = {
        'bool': {
            'must': [
                {
                    'multi_match': {
                        'type': 'phrase', 
                        'query': query, 
                        'fields': weight_fields
                    }
                }
            ],
            'boost': 1.1
        }
    }
    phrase_query['dis_max']['queries'].append(should)

    # 2. create all two-phrase combinations of the query and append to "should"
    number_of_tokens = len(query_words)
    if number_of_tokens > 2 and number_of_tokens < 11:
        for cut in range(1, number_of_tokens):
            phrase1 = ' '.join(query_words[0:cut])
            phrase2 = ' '.join(query_words[cut:])
            # add a phrase pair in "must" which will go inside "should"
            must = []
            for phrase in [phrase1, phrase2]:
                must.append ({
                        "multi_match": {
                            "type": "phrase",
                            "query": phrase,
                            "fields": weight_fields
                        }
                        })
            # append the pair to "should"
            phrase_query['dis_max']['queries'].append({'bool': {'must': must}})

    #print(json.dumps(phrase_query, indent=2))
    return(phrase_query)

# remove stopwords from query
def stopwords(query):
    prefixes = [
        "mkhan [pm]o ", "rgya gar kyi ", "mkhan chen ", "a lag ", "a khu ", "rgan ", "rgan lags ", 
        "zhabs drung ", "mkhas grub ", "mkhas dbang ", "mkhas pa ", "bla ma ", "sman pa ", "em chi ", 
        "yongs 'dzin ", "ma hA ", "sngags pa ", "sngags mo ", "sngags pa'i rgyal po ", "sems dpa' chen po ", 
        "rnal 'byor [pm]a ", "rje ", "rje btsun ", "rje btsun [pm]a ", "kun mkhyen ", "lo tsA ba ", "lo tswa ba ", 
        "lo cA ba ", "lo chen ", "slob dpon ", "paN\\+Di ta ", "paN chen ", "srI ", "dpal ", "dge slong ", 
        "dge slong ma ", "dge bshes ", "dge ba'i bshes gnyen ", "shAkya'i dge slong ", "'phags pa ", "A rya ", 
        "gu ru ", "sprul sku ", "a ni ", "a ni lags ", "rig 'dzin ", "chen [pm]o ", "A tsar\\+yA ", "gter ston ", 
        "gter chen ", "thams cad mkhyen pa ", "rgyal dbang ", "rgyal ba ", "btsun [pm]a ", "dge rgan ", 
        "theg pa chen po'i ", "hor ", "sog [pm]o ", "sog ", "a lags sha ", "khal kha ", "cha har ", "jung gar ", 
        "o rad ", "hor chin ", "thu med ", "hor pa ", "na'i man ", "ne nam ", "su nyid ", "har chen ",
        "bdrc[^a-zA-Z0-9]*", "bdr: *", "tbrc[^a-zA-Z0-9]*"
    ]
    suffixes = [
        " dpal bzang po", " lags", " rin po che", " sprul sku", " le'u", " rgyud kyi rgyal po", 
        " bzhugs so", " sku gzhogs", " (c|[sz])es bya ba"
    ]

    prefix_match = '^(' + '|'.join(prefixes) + ')'
    suffix_match = '(' + '|'.join(suffixes) + ')$'

    query = re.sub(prefix_match, '', query, flags=re.I)
    query = re.sub(suffix_match, '', query, flags=re.I)
    return query

def autosuggest_json(query, scope='all'):
    os_json = {
        "suggest": {
            "autocomplete": {
                "prefix": query,
                "completion": {
                    "field": "suggest_me",
                    "size": 10,
                    "fuzzy" : {
                        "fuzziness" : "AUTO"
                    },
                    "skip_duplicates": True,
                    "contexts": {
                        "scope": scope
                    }
                }
            }
        }
    }
    return(os_json)

def do_search(os_json, index):
    headers = {'Content-Type': 'application/json'}
    auth = (os.environ['OPENSEARCH_USER'], os.environ['OPENSEARCH_PASSWORD'])
    url = os.environ['OPENSEARCH_URL'] + f'/{index}/_search'
    r = requests.post(url, headers=headers, auth=auth, json=os_json, timeout=1, verify=False)
    return r.json()

def tibetan(query):
    if re.search(r'[\u0F00-\u0FFF]', query):
        from pyewts import pyewts
        converter = pyewts()
        query = converter.toWylie(query)
        return query, True
    else:
        return query, False

def suggestion_highlight(user_input, suggestion):
    # user input matches suggestion
    if suggestion.startswith(user_input):
        return re.sub(f'^{user_input}(.*)$', fr'{user_input}<suggested>\1</suggested>', suggestion)
    # first part of user input matches suggestion
    for i in range(0, min(len(suggestion), len(user_input))):
        if user_input[i] != suggestion[i]:
            return suggestion[:i] + '<suggested>' + suggestion[i:] + '</suggested>'
    # could not highlight
    return suggestion

def id_json_autosuggest(query):
    os_json = {
        "query": {
            "bool": {
                "should": [
                    {
                        "term": {
                            "_id": query
                        }
                    },
                    {
                        "term": {
                            "other_id": query
                        }
                    },
                    {
                        "term": {
                            "graphs": query
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    }
    return os_json

def id_json_search(query):
    match_phrases = []
    if ' ' in query:
        id_code, label = re.split(' ', query, maxsplit=1)
        label = re.sub(';.*$', '', label)
        for field in [f for f in get_fields('as_list') if f.startswith('prefLabel_')]:
            match_phrases.append({'match_phrase': {field: label}})
    else:
        id_code = query

    os_json = {
        "bool": {
            "must": [
                {
                    "bool": {
                        "should": [
                            {
                                "term": {
                                    "_id": id_code
                                }
                            },
                            {
                                "term": {
                                    "other_id": id_code
                                }
                            },
                            {
                                "term": {
                                    "graphs": id_code
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                }
            ]
        }
    }
    if match_phrases:
        os_json['bool']['must'].append({'bool': {'should': match_phrases, 'minimum_should_match': 1}})

    #print(json.dumps(os_json, indent=4))
    return os_json

def get_query_obj(query_str):
    query_str = query_str.strip()
    query_str, is_tibetan = tibetan(query_str)
    if not is_tibetan:
        query_str = re.sub("[‘’‛′‵ʼʻˈˊˋ`]", "'", query_str)
    query_str = stopwords(query_str)

    # id search
    if re.search(r'(\S\d)', query_str):
        return id_json_search(query_str)
    # normal search
    else:
        return phrase_match_json(query_str)

def format_query_rec(query):
    if isinstance(query, list):
        res = []
        for item in query:
            res.append(format_query_rec(item))
        return res
    # we assume query is an object
    res = {}
    for key, value in query.items():
        if key == "bdrc-query":
            repl = get_query_obj(value)
            for key_repl, value_repl in repl.items():
                res[key_repl] = value_repl
        elif isinstance(value, dict) or isinstance(value, list):
            res[key] = format_query_rec(value)
        else:
            res[key] = value
    return res

def format_query(data):
    query = format_query_rec(data["query"])
    data["query"] = query
    return data

@app.route('/autosuggest', methods=['POST', 'GET'])
def autosuggest():
    data = request.json
    print(data)
    query = data['query'].strip()
    query, is_tibetan = tibetan(query)
    if not is_tibetan:
        query = re.sub("[‘’‛′‵ʼʻˈˊˋ`]", "'", query)

    # id in autosuggest
    if re.search('(\S\d)', query):
        os_json = id_json_autosuggest(query)
        r = do_search(os_json, 'bdrc_prod')
        result = []
        for hit in r['hits']['hits']:
            labels = []
            for field, value in hit['_source'].items():
                if field.startswith('prefLabel'):
                    labels.append(value[0].strip())
            result.append(query + ' ' + '; '.join(labels))
        return result

    os_json = autosuggest_json(query)
    #print(json.dumps(os_json, indent=4))
    r = do_search(os_json, 'bdrc_autosuggest')

    results = []
    hits = r['suggest']['autocomplete'][0]['options']
    for hit in hits:
        results.append({'lang': hit['_source'].get('lang'), 'res': suggestion_highlight(query, hit['text'])})
    #print(results)
    return results

# normal search
@app.route('/search', methods=['POST', 'GET'])
def normal_search():
    data = request.json

    os_json = format_query(data)
    #print(json.dumps(os_json, indent=4))

    results = do_search(os_json, 'bdrc_prod')
    print(json.dumps(results, indent=4))
    
    return results

def test_format_query():
    query_json_str = """
    {
       "query":{
          "function_score":{
             "script_score":{
                "script":{
                   "id":"bdrc-score"
                }
             },
             "query":{
                "bool":{
                   "filter":[
                      {
                         "bool":{
                            "should":[
                               {
                                  "range":{
                                     "etext_quality":{
                                        "gte":"3.99",
                                        "lte":"4.01"
                                     }
                                  }
                               }
                            ]
                         }
                      }
                   ],
                   "bdrc-query":"spyod 'jug"
                }
             }
          }
       }
    }
    """
    query = json.loads(query_json_str)
    print(json.dumps(format_query_rec(query)))

if __name__ == '__main__':
    #test_format_query()
    app.run(debug=True, port=5000)