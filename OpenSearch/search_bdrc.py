import json, re, requests, pyewts
from requests.auth import HTTPBasicAuth
from flask import Flask, request
from flask_cors import CORS
import os
import jsonlines
import io
# suppress redundant messages in local
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from pyewts import pyewts
CONVERTER = pyewts()

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes

def get_fields(structure, langs=['bo_x_ewts', 'en']):
    # fields in the descending order of occurrences in the index
    # use the order to limit the number of fields when the full list would be too long (requires python 3.7)
    all_fields = {"prefLabel_bo_x_ewts": 1, "altLabel_bo_x_ewts": 0.6, "comment_bo_x_ewts": 0.0001, "author": 0.1, "comment_en": 0.0001, "authorshipStatement_bo_x_ewts": 0.005, "summary_en": 0.2, "altLabel_cmg_x_poppe": 0.6, "prefLabel_en": 1, "altLabel_cmg_mong": 0.6, "prefLabel_km": 1, "publisherName_bo_x_ewts": 0.01, "comment": 0.0001, "publisherLocation_bo_x_ewts": 0.01, "prefLabel_zh_hani": 1, "authorshipStatement_en": 0.005, "prefLabel_km_x_twktt": 1, "publisherLocation_en": 0.01, "altLabel_zh_latn_pinyin_x_ndia": 0.6, "publisherName_en": 0.01, "seriesName_res": 0.1, "altLabel_en": 0.6, "summary_bo_x_ewts": 0.2, "altLabel_km": 0.6, "seriesName_bo_x_ewts": 0.1, "issueName": 0.1, "altLabel_km_x_twktt": 0.6, "prefLabel_pi_khmr": 1, "altLabel_zh_hani": 0.6, "prefLabel_zh_latn_pinyin_x_ndia": 1, "translator": 0.1, "altLabel_sa_x_iast": 0.6, "prefLabel_sa_x_ndia": 1, "prefLabel_sa_alalc97": 1, "prefLabel_sa_x_iast": 1, "prefLabel_pi_x_twktt": 1, "seriesName_en": 0.1, "altLabel_pi_khmr": 0.6, "altLabel_pi_x_twktt": 0.6, "publisherName_zh_hani": 0.01, "altLabel_sa_x_ndia": 0.6, "prefLabel_zh_latn_wadegile": 1, "publisherLocation_zh_hani": 0.01, "altLabel_bo_alalc97": 0.6, "seriesName_zh_hani": 0.1, "prefLabel_mn_x_trans": 1, "altLabel_mn_x_trans": 0.6, "authorshipStatement_zh_hani": 0.005, "prefLabel": 1, "altLabel_zh_latn_pinyin": 0.6, "comment_zh_hani": 0.0001, "altLabel_sa_alalc97": 0.6, "prefLabel_mn_alalc97": 1, "prefLabel_sa_deva": 1, "altLabel_zh_latn_wadegile": 0.6, "publisherLocation_zh_latn_pinyin_x_ndia": 0.01, "authorshipStatement_zh_latn_pinyin_x_ndia": 0.005, "publisherName_zh_latn_pinyin_x_ndia": 0.01, "prefLabel_zh_latn_pinyin": 1, "comment_sa_x_iast": 0.0001, "altLabel_mn_alalc97": 0.6, "seriesName_zh_latn_pinyin_x_ndia": 0.1, "prefLabel_bo_alalc97": 1, "prefLabel_mn": 1, "prefLabel_pi_x_iast": 1, "prefLabel_sa_x_trans": 1, "prefLabel_fr": 1, "summary_zh_hani": 0.2, "altLabel_mn": 0.6, "altLabel_sa_deva": 0.6, "prefLabel_bo_latn_wadegile": 1, "publisherName_bo_latn_wadegile": 0.01, "altLabel_bo_latn_wadegile": 0.6, "comment_bo_latn_wadegile": 0.0001, "prefLabel_ja": 1, "altLabel_bo_latn_pinyin": 0.6, "publisherName_fr": 0.01, "authorshipStatement_zh": 0.005, "prefLabel_fr_alalc97": 1, "prefLabel_km_x_unspec": 1, "prefLabel_ru": 1, "prefLabel_sa_x_phon_en_m_tbrc": 1, "prefLabel_sa_x_rma": 1, "prefLabel_zh_alalc97": 1, "summary_sa_x_ndia": 0.2, "altLabel_bo_x_ndia": 0.6, "altLabel_de": 0.6, "altLabel_ja_alalc97": 0.6, "altLabel_ja_x_ndia": 0.6, "altLabel_km_x_unspec": 0.6, "altLabel_pi_x_iast": 0.6, "altLabel_sa_x_rma": 0.6, "altLabel_sa_x_trans": 0.6, "altLabel_zh_alalc97": 0.6, "altLabel_zh_x_ndia": 0.6, "authorshipStatement_sa_deva": 0.005, "authorshipStatement_zh_alalc97": 0.005, "comment_bo_alalc97": 0.0001, "comment_bo_x_ndia": 0.0001, "comment_sa_deva": 0.0001, "comment_sa_x_ndia": 0.0001, "comment_zh_latn_pinyin": 0.0001, "prefLabel_bo_x_acip": 1, "prefLabel_de": 1, "prefLabel_fr_x_iast": 1, "prefLabel_ja_alalc97": 1, "prefLabel_ja_x_ndia": 1, "prefLabel_ru_alalc97": 1, "publisherLocation_bo_latn_wadegile": 0.01, "publisherLocation_fr": 0.01, "publisherLocation_mn_alalc97": 0.01, "publisherLocation_sa_deva": 0.01, "publisherName_sa_deva": 0.01, "publisherName_sa_x_iast": 0.01}

    fields = {k: v for k, v in all_fields.items() if any(k.endswith(lang) for lang in langs)}

    if structure == 'with_weights':
        return [f'{name}^{weight}' for name, weight in list(fields.items())]
    elif structure == 'for_autosuggest_highlight':
        return {key: {} for key in list(fields.keys())}
    elif structure == 'as_list':
        return fields.keys()
    elif structure == 'as_dict':
        return dict(list(fields.items()))

def fuzzy_phrase_json(query_str):

    # We are here because the query did not match anything.
    # First, get similar phrases from bdrc_autosuggest with fuzzy match
    os_json = autosuggest_json(query_str)
    r = do_search(os_json, 'bdrc_autosuggest')
    try: hits = r['suggest']['autocomplete'][0]['options']
    except KeyError:
        return None
    matches = set()
    length = len(re.split("[^a-zA-Z0-9+']", query_str))
    for hit in hits:
        matches.add(' '.join(re.split("[^a-zA-Z0-9+']", hit['text'])[:length]))
    if not matches:
        return None

    # Now we have phrases that do exist in bdrc_prod
    # Query bdrc_prod to find them
    weight_fields = get_fields('with_weights')
    fuzzy_phrase_query = {
        "dis_max": {
            "queries": []
        }
    }

    for match in matches:
        should = {
            'bool': {
                'must': [
                    {
                        'multi_match': {
                            'type': 'phrase', 
                            'query': match, 
                            'fields': weight_fields
                        }
                    }
                ],
                'boost': 1
            }
        }
        fuzzy_phrase_query['dis_max']['queries'].append(should)
    return fuzzy_phrase_query

def phrase_match_json(query_str):
    query_words = re.split('[ /_]+', query_str)
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
                        'query': query_str, 
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
            if phrase2 in ["tu", "du", "su", "gi", "kyi", "gyi", "gis", "kyis", "gyis", "kyang", "yang", "ste", "de", "te", "go", "ngo", "do", "no", "bo", "ro", "so", "'o", "to", "pa", "ba", "gin", "kyin", "gyin", "yin", "c'ing", "zh'ing", "sh'ing", "c'ig", "zh'ig", "sh'ig", "c'e'o", "zh'e'o", "sh'e'o", "c'es", "zh'es", "pas", "pa'i", "pa'o", "bas", "ba'i", "la"]:
                continue
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
def stopwords(query_str):
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

    query_str = re.sub(prefix_match, '', query_str, flags=re.I)
    query_str = re.sub(suffix_match, '', query_str, flags=re.I)
    return query_str

def autosuggest_json(query_str, scope='all'):
    os_json = {
        "suggest": {
            "autocomplete": {
                "prefix": query_str,
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
    if __name__ != '__main__':
        return os_json
    headers = {'Content-Type': 'application/json'}
    auth = (os.environ['OPENSEARCH_USER'], os.environ['OPENSEARCH_PASSWORD'])
    url = os.environ['OPENSEARCH_URL'] + f'/{index}/_search'
    r = requests.post(url, headers=headers, auth=auth, json=os_json, timeout=5, verify=False)
    return r.json()

def jsons_to_ndjsonbytes(jsons):
    fp = io.BytesIO()  # file-like object
    with jsonlines.Writer(fp) as writer:
        for j in jsons:
            writer.write(j)
    b =  fp.getvalue()
    fp.close()
    return b

def do_msearch(os_jsons, index):
    ndjson = jsons_to_ndjsonbytes(os_jsons)
    headers = {'Content-Type': 'application/x-ndjson'}
    auth = (os.environ['OPENSEARCH_USER'], os.environ['OPENSEARCH_PASSWORD'])
    url = os.environ['OPENSEARCH_URL'] + f'/{index}/_msearch'
    r = requests.post(url, headers=headers, auth=auth, data=ndjson, timeout=5, verify=False)
    return r.json()

def tibetan(query_str):
    if re.search(r'[\u0F00-\u0FFF]', query_str):
        query_str = CONVERTER.toWylie(query_str)
        return query_str, True
    else:
        return query_str, False

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

def id_json_autosuggest(query_str):
    os_json = {
        "query": {
            "bool": {
                "should": [
                    {
                        "term": {
                            "_id": query_str
                        }
                    },
                    {
                        "term": {
                            "other_id": query_str
                        }
                    },
                    {
                        "term": {
                            "graphs": query_str
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    }
    return os_json

def id_json_search(query_str):
    match_phrases = []
    if ' ' in query_str:
        id_code, label = re.split(' ', query_str, maxsplit=1)
        label = re.sub(';.*$', '', label)
        for field in [f for f in get_fields('as_list') if f.startswith('prefLabel_')]:
            match_phrases.append({'match_phrase': {field: label}})
    else:
        id_code = query_str

    os_json = {
        "query": {
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
    }
    if match_phrases:
        os_json['query']['bool']['must'].append({'bool': {'should': match_phrases, 'minimum_should_match': 1}})

    return os_json

# not in use
def find_bdrc_query_rec(json_obj):
    if 'query' in json_obj and isinstance(json_obj['query'], str):
        return json_obj['query']
    for key, value in json_obj.items():
        if isinstance(value, dict):
            result = find_bdrc_query_rec(value)
            if result is not None:
                return result
    return None

def replace_bdrc_query(json_obj, replacement):
    try: json_obj["query"]["function_score"]["query"]["bool"]["must"] = [replacement]
    except KeyError:
        print('json_ob', json_obj)
        print('replacement', replacement)
    return json_obj

def get_query_str(data):
    # get query string from searchkit json
    query_str = None
    try:
        query_str = data["query"]["function_score"]["query"]["bool"]["must"][0]["multi_match"]["query"]
    except KeyError:
        return None

    # clean up query string
    query_str = query_str.strip()
    query_str, is_tibetan = tibetan(query_str)

    if not is_tibetan:
        query_str = re.sub("[‘’‛′‵ʼʻˈˊˋ`]", "'", query_str)
    query_str = re.sub('[/_]+$', '', query_str)
    query_str = stopwords(query_str)

    return query_str

@app.route('/autosuggest', methods=['POST', 'GET'])
def autosuggest():
    data = request.json
    query_str = data['query'].strip()
    query_str, is_tibetan = tibetan(query_str)
    if not is_tibetan:
        query_str = re.sub("[‘’‛′‵ʼʻˈˊˋ`]", "'", query_str)

    # id in autosuggest
    if re.search(r'([^\s0-9]\d)', query_str):
        os_json = id_json_autosuggest(query_str)
        r = do_search(os_json, 'bdrc_prod')
        results = []
        for hit in r['hits']['hits']:
            labels = []
            for field, value in hit['_source'].items():
                if field.startswith('prefLabel'):
                    labels.append(value[0].strip())
            results.append({'lang': hit['_source'].get('lang'), 'res': query_str + ' ' + '; '.join(labels)})
            #result.append(query_str + ' ' + '; '.join(labels))
        return results

    os_json = autosuggest_json(query_str)
    #print(json.dumps(os_json, indent=4))
    r = do_search(os_json, 'bdrc_autosuggest')

    results = []
    hits = r['suggest']['autocomplete'][0]['options']
    for hit in hits:
        results.append({'lang': hit['_source'].get('lang'), 'res': suggestion_highlight(query_str, hit['text'])})
    #print(results)
    return results

# normal search
@app.route('/search', methods=['POST', 'GET'])
def normal_search(test_json=None):
    # unit test
    if test_json:
        data = test_json
    # production
    else:
        data = request.json
    query_str = get_query_str(data)

    # id search
    if re.search(r'([^\s0-9]\d)', query_str):
        data = id_json_search(query_str)
        results = do_search(data, 'bdrc_prod')
        return results

    # normal search
    else:
        phrase_json = phrase_match_json(query_str)
        data = replace_bdrc_query(data, phrase_json)

    results = do_search(data, 'bdrc_prod')

    # zero hits, try fuzzy phrase
    if __name__ == '__main__' and results['hits']['total']['value'] == 0:
        fuzzy_json = fuzzy_phrase_json(query_str)
        if fuzzy_json:
            data = replace_bdrc_query(request.json, fuzzy_json)
            results = do_search(data, 'bdrc_prod')

    return results

def tweak_query(data, fuzzy=False):
    query_str = get_query_str(data)
    # id search
    if not fuzzy and re.search(r'([^\s0-9]\d)', query_str):
        return id_json_search(query_str)
    if not fuzzy:
        phrase_json = phrase_match_json(query_str)
        return replace_bdrc_query(data, phrase_json)
    fuzzy_json = fuzzy_phrase_json(query_str)
    if fuzzy_json:
        return replace_bdrc_query(request.json, fuzzy_json)
    return None

def tweak_mquery(jsons, fuzzy=False):
    res = []
    for i, j in enumerate(jsons):
        if i % 2 == 0:
            res.append(j)
        else:
            tweaked = tweak_query(j)
            if tweaked is None:
                return None
            res.append(tweaked)
    return res

# normal search
@app.route('/msearch', methods=['POST', 'GET'])
def normal_msearch():
    original_jsons = []
    fp = io.BytesIO(request.data)
    with jsonlines.Reader(fp) as reader:
        for obj in reader:
            original_jsons.append(obj)
    fp.close()

    normal_tweaks = tweak_mquery(original_jsons)
    results = do_msearch(normal_tweaks, 'bdrc_prod')

    if results["responses"][0]['hits']['total']['value'] == 0:
        fuzzy_tweaks = tweak_mquery(original_jsons, fuzzy=True)
        if fuzzy_tweaks is not None:
            results = do_msearch(fuzzy_tweaks, 'bdrc_prod')
    
    return results

if __name__ == '__main__':
    app.run(debug=True, port=5000)