import json, re, requests
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

# we only return a certain number of hits per etext in the general search
INNER_HITS_SIZE = 3

def find_string_value(json_obj, key):
    if isinstance(json_obj, dict):
        for k, v in json_obj.items():
            if k == key:
                if isinstance(v, str):
                    return v
            result = find_string_value(v, key)
            if result is not None:
                return result
    elif isinstance(json_obj, list):
        for item in json_obj:
            result = find_string_value(item, key)
            if result is not None:
                return result
    return None

def remove_etext_filter(data):
    if isinstance(data, list):
        return [item for item in (remove_etext_filter(item) for item in data) if item is not None]
    elif isinstance(data, dict):
        if data == {"term": {"etext_search": "true"}}:
            return None
        return {k: remove_etext_filter(v) for k, v in data.items() if remove_etext_filter(v) is not None}
    else:
        return data

def get_fields(structure, langs=['bo_x_ewts', 'en']):
    # if more than two languages, the two-phrase match starts reducing phrase pairs to avoid too big queries, and search suffers
    all_fields = {"prefLabel_bo_x_ewts": 1, "altLabel_bo_x_ewts": 0.6, "comment_bo_x_ewts": 0.0001, "author": 0.1, "comment_en": 0.00005, "authorshipStatement_bo_x_ewts": 0.005, "summary_en": 0.1, "altLabel_cmg_x_poppe": 0.6, "prefLabel_en": 0.5, "altLabel_cmg_mong": 0.6, "prefLabel_km": 1, "publisherName_bo_x_ewts": 0.01, "comment": 0.0001, "publisherLocation_bo_x_ewts": 0.01, "prefLabel_zh_hani": 1, "authorshipStatement_en": 0.00025, "prefLabel_km_x_twktt": 1, "publisherLocation_en": 0.005, "altLabel_zh_latn_pinyin_x_ndia": 0.6, "publisherName_en": 0.005, "seriesName_res": 0.1, "altLabel_en": 0.3, "summary_bo_x_ewts": 0.2, "altLabel_km": 0.6, "seriesName_bo_x_ewts": 0.1, "issueName": 0.1, "altLabel_km_x_twktt": 0.6, "prefLabel_pi_khmr": 1, "altLabel_zh_hani": 0.6, "prefLabel_zh_latn_pinyin_x_ndia": 1, "translator": 0.1, "altLabel_sa_x_iast": 0.6, "prefLabel_sa_x_ndia": 1, "prefLabel_sa_alalc97": 1, "prefLabel_sa_x_iast": 1, "prefLabel_pi_x_twktt": 1, "seriesName_en": 0.05, "altLabel_pi_khmr": 0.6, "altLabel_pi_x_twktt": 0.6, "publisherName_zh_hani": 0.01, "altLabel_sa_x_ndia": 0.6, "prefLabel_zh_latn_wadegile": 1, "publisherLocation_zh_hani": 0.01, "altLabel_bo_alalc97": 0.6, "seriesName_zh_hani": 0.1, "prefLabel_mn_x_trans": 1, "altLabel_mn_x_trans": 0.6, "authorshipStatement_zh_hani": 0.005, "prefLabel": 1, "altLabel_zh_latn_pinyin": 0.6, "comment_zh_hani": 0.0001, "altLabel_sa_alalc97": 0.6, "prefLabel_mn_alalc97": 1, "prefLabel_sa_deva": 1, "altLabel_zh_latn_wadegile": 0.6, "publisherLocation_zh_latn_pinyin_x_ndia": 0.01, "authorshipStatement_zh_latn_pinyin_x_ndia": 0.005, "publisherName_zh_latn_pinyin_x_ndia": 0.01, "prefLabel_zh_latn_pinyin": 1, "comment_sa_x_iast": 0.0001, "altLabel_mn_alalc97": 0.6, "seriesName_zh_latn_pinyin_x_ndia": 0.1, "prefLabel_bo_alalc97": 1, "prefLabel_mn": 1, "prefLabel_pi_x_iast": 1, "prefLabel_sa_x_trans": 1, "prefLabel_fr": 1, "summary_zh_hani": 0.2, "altLabel_mn": 0.6, "altLabel_sa_deva": 0.6, "prefLabel_bo_latn_wadegile": 1, "publisherName_bo_latn_wadegile": 0.01, "altLabel_bo_latn_wadegile": 0.6, "comment_bo_latn_wadegile": 0.0001, "prefLabel_ja": 1, "altLabel_bo_latn_pinyin": 0.6, "publisherName_fr": 0.01, "authorshipStatement_zh": 0.005, "prefLabel_fr_alalc97": 1, "prefLabel_km_x_unspec": 1, "prefLabel_ru": 1, "prefLabel_sa_x_phon_en_m_tbrc": 0.5, "prefLabel_sa_x_rma": 1, "prefLabel_zh_alalc97": 1, "summary_sa_x_ndia": 0.2, "altLabel_bo_x_ndia": 0.6, "altLabel_de": 0.6, "altLabel_ja_alalc97": 0.6, "altLabel_ja_x_ndia": 0.6, "altLabel_km_x_unspec": 0.6, "altLabel_pi_x_iast": 0.6, "altLabel_sa_x_rma": 0.6, "altLabel_sa_x_trans": 0.6, "altLabel_zh_alalc97": 0.6, "altLabel_zh_x_ndia": 0.6, "authorshipStatement_sa_deva": 0.005, "authorshipStatement_zh_alalc97": 0.005, "comment_bo_alalc97": 0.0001, "comment_bo_x_ndia": 0.0001, "comment_sa_deva": 0.0001, "comment_sa_x_ndia": 0.0001, "comment_zh_latn_pinyin": 0.0001, "prefLabel_bo_x_acip": 1, "prefLabel_de": 1, "prefLabel_fr_x_iast": 1, "prefLabel_ja_alalc97": 1, "prefLabel_ja_x_ndia": 1, "prefLabel_ru_alalc97": 1, "publisherLocation_bo_latn_wadegile": 0.01, "publisherLocation_fr": 0.01, "publisherLocation_mn_alalc97": 0.01, "publisherLocation_sa_deva": 0.01, "publisherName_sa_deva": 0.01, "publisherName_sa_x_iast": 0.01}

    fields = {k: v for k, v in all_fields.items() if any(k.endswith(lang) for lang in langs)}

    if structure == 'with_weights':
        return [f'{name}^{weight}' for name, weight in list(fields.items())]
    elif structure == 'for_autosuggest_highlight':
        return {key: {} for key in list(fields.keys())}
    elif structure == 'as_list':
        return fields.keys()
    elif structure == 'as_dict':
        return dict(list(fields.items()))

def and_json(query_str, query_str_bo):
    phrases = re.split(' AND ', query_str)
    phrases_bo = re.split('AND', query_str_bo)

    fields = get_fields('with_weights')

    must = []
    # divide in phrases at AND
    # the `min()` prevents out of range error, which should never happen
    for n in range(0, min(len(phrases), len(phrases_bo))):
        should = []

        # match metadata
        should.append({"multi_match": {"query": phrases[n], "fields": fields, "type": "phrase"}})

        # match en in etext
        has_child = {"has_child": {
            "type": "etext",
            "query": {"nested": {"path": "chunks", "query": {"match_phrase": {"chunks.text_en": phrases[n]}}}}, 
            "inner_hits": {"size": INNER_HITS_SIZE,"_source": {"includes": ["id"]}, "highlight": {"fields": {"chunks.text_en": {}}}, "name": "phrase"+str(n+1)}, 
            "boost": 1}}
        should.append(has_child)

        # match bo in etext
        has_child = {"has_child": {
            "type": "etext",
            "query": {"nested": {"path": "chunks", "query": {"match_phrase": {"chunks.text_bo": phrases_bo[n]}}}}, 
            "inner_hits": {"size": INNER_HITS_SIZE,"_source": {"includes": ["id"]}, "highlight": {"fields": {"chunks.text_bo": {}}}, "name": "phrase_bo"+str(n+1)}, 
            "boost": 1}}
        should.append(has_child)

        # append shoulds to must, which produces the intended AND
        must.append({"bool": {"should": should}})

    json_obj = {
        "bool": {
            "must": must
        }
    }

    return json_obj

def big_json(query_str, query_str_bo):
    # all queries go to "queries" under "dis_max"
    big_query = {
        "dis_max": {
            "queries": []
        }
    }

    # 1. Get phrases from bdrc_autosuggest with fuzzy match.
    # This is a workaround to emulate fuzzy phrase match
    os_json = autosuggest_json(query_str)
    r = do_search(os_json, 'bdrc_autosuggest')
    try: hits = r['suggest']['autocomplete'][0]['options']
    except KeyError:
        hits = []
    matches = set()
    length = len(re.split("[^a-zA-Z0-9+']", query_str))
    for hit in hits:
        matches.add(' '.join(re.split("[^a-zA-Z0-9+']", hit['text'])[:length]))

    weight_fields = get_fields('with_weights')
    # Now we have phrases that do exist in bdrc_prod and fuzzy match the query string
    # Add them to the query if not identical
    for match in matches:
        if match.lower() != query_str.lower():
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
                    'boost': 0.8
                }
            }
            big_query['dis_max']['queries'].append(should)

    # 2. full query perfect match
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
    big_query['dis_max']['queries'].append(should)

    # 3. etext match
    big_query['dis_max']['queries'].append(etext_json(query_str, query_str_bo))

    # 4. create all two-phrase combinations of the keywords
    query_words = re.split("[^a-zA-Z0-9+']", query_str)
    number_of_tokens = len(query_words)
    if number_of_tokens > 2:
        for cut in range(1, number_of_tokens):
            # limit query length to avoid OS error
            if len(big_query['dis_max']['queries']) * number_of_tokens < 180:
                phrase1 = ' '.join(query_words[:cut])
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
                            "fields": get_fields('with_weights', ['bo_x_ewts'])
                        }
                    })
                # append the pair to "should"
                    big_query['dis_max']['queries'].append({'bool': {'must': must}})

    #print(json.dumps(big_query, indent=2))
    return(big_query)

def etext_json(query_str, query_str_bo):
    json_obj = {
        "bool": {
            "must": [
                {
                    "has_child": {
                        "type": "etext",
                        "query": {
                            "nested": {
                                "path": "chunks",
                                "query": {
                                    "bool": {
                                        "should": [
                                            {
                                                "match_phrase": {
                                                    "chunks.text_bo": query_str_bo
                                                }
                                            },
                                            {
                                                "match_phrase": {
                                                    "chunks.text_en": query_str
                                                }
                                            }
                                        ]
                                    }
                                },
                                "inner_hits": {
                                    "highlight": {
                                        "fields": {
                                            "chunks.text_bo": {
                                                "highlight_query": {
                                                    "match_phrase": {
                                                        "chunks.text_bo": query_str_bo
                                                    }
                                                }
                                            },
                                            "chunks.text_en": {
                                                "highlight_query": {
                                                    "match_phrase": {
                                                        "chunks.text_en": query_str
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "inner_hits": {
                            "size": INNER_HITS_SIZE,
                            "_source": {
                                "includes": ["etext_instance", "etext_pagination_in", "etext_imagegroup", "etext_vol", "volumeNumber"]
                            },
                            "highlight": {
                                "fields": {
                                    "chunks.text_bo": {
                                        "highlight_query": {
                                            "match_phrase": {
                                                "chunks.text_bo": query_str_bo
                                            }
                                        }
                                    },
                                    "chunks.text_en": {
                                        "highlight_query": {
                                            "match_phrase": {
                                                "chunks.text_en": query_str
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            ],
            "boost": 1
        }
    }
    return json_obj

PREFIX_PAT = None
SUFFIX_PAT = None

def stopwords(query_str):
    global PREFIX_PAT, SUFFIX_PAT
    if PREFIX_PAT is None:
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

        PREFIX_PAT = re.compile('^(' + '|'.join(prefixes) + ')', flags=re.I)
        SUFFIX_PAT = re.compile('(' + '|'.join(suffixes) + ')$', flags=re.I)

    query_str = re.sub(PREFIX_PAT, '', query_str)
    query_str = re.sub(SUFFIX_PAT, '', query_str)
    return query_str

def autosuggest_json(query_str, scope=['all']):
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
                    "skip_duplicates": True
                }
            }
        }
    }
    if scope:
        os_json['suggest']['autocomplete']['completion']['contexts'] = {'scope': scope}
    return(os_json)

def do_search(os_json, index):
    headers = {'Content-Type': 'application/json'}
    auth = (os.environ['OPENSEARCH_USER'], os.environ['OPENSEARCH_PASSWORD'])
    url = os.environ['OPENSEARCH_URL'] + f'/{index}/_search'
    r = requests.post(url, headers=headers, auth=auth, json=os_json, timeout=30, verify=False)
    if r.status_code != 200:
        print(r.status_code, r.text)
    return r.json()

def do_msearch(jsons, index):
    headers = {'Content-Type': 'application/x-ndjson'}
    auth = (os.environ['OPENSEARCH_USER'], os.environ['OPENSEARCH_PASSWORD'])
    url = os.environ['OPENSEARCH_URL'] + f'/{index}/_msearch'
    ndjson = '\n'.join(json.dumps(x) for x in jsons) + '\n'
    r = requests.post(url, headers=headers, auth=auth, data=ndjson, timeout=30, verify=False)
    if r.status_code != 200:
        print('Error from Opensearch:', r.status_code, r.text)
    return r.json()

def convert_tibetan(query_str):
    # convert combinations of tibetan unicode and ascii to pure unicode and pure ascii
    wylie = re.sub(r'([\u0F00-\u0FFF]+)', lambda m: CONVERTER.toWylie(m.group(1)), query_str)
    unicode = re.sub(r'([^\u0F00-\u0FFF]+)', lambda m: CONVERTER.toUnicode(m.group(1)), re.sub('AND', 'ཧྵ', query_str))
    unicode = re.sub('ཧྵ', 'AND', unicode)
    return wylie, unicode

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

def id_json_autosuggest(query_str, scope=['all']):
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

    if scope != ['all']:
        os_json['query']['bool']['filter'] = {'terms': {'associated_res': scope}}

    return os_json

def id_json_search(query_str, original_jsons):
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

    return [original_jsons[0], os_json]

def replace_bdrc_query(json_obj, replacement):
    for n in range(1, len(json_obj), 2):
        try: json_obj[n]["query"]["function_score"]["query"]["bool"]["must"] = [replacement]
        except KeyError:
            print('json_ob', json_obj)
            print('replacement', replacement)
    return json_obj

def get_query_str(data):
    # prepare in-etext query string
    if isinstance(data, str):
        query_str = data
    # get query string from searchkit json
    else:
        query_str = find_string_value(data, 'query')
        if not query_str:
            return query_str

    query_str = query_str.strip()

    query_str_ascii, query_str_bo = convert_tibetan(query_str)

    query_str_ascii = re.sub("[‘’‛′‵ʼʻˈˊˋ`]", "'", query_str_ascii)    
    query_str_ascii = re.sub('[/_]+$', '', query_str_ascii)
    query_str_ascii = stopwords(query_str_ascii)
    query_str_ascii = re.sub('^(t[oö]hoku|t[oö]h)[ .:]+(\d+)$', r'd\2', query_str_ascii, flags=re.IGNORECASE)

    # TODO convert 9th to 09
    # convert 9 to 09

    #print(query_str_ascii, query_str_bo)
    return query_str_ascii, query_str_bo

def is_etext_only(original_jsons):
    for one_json in original_jsons:
        if find_string_value(one_json, 'etext_search') == 'true':
            return True
    return False

def print_jsons(print_me, place='', query_str=None):
    # export OPENSEARCH_PRINT="tests" to recreate tests
    if os.getenv('OPENSEARCH_PRINT') == 'tests':
        # save searchkit jsons in ./tests
        if isinstance(print_me, list):
            with open('tests/' + query_str + '.json', 'w') as f:
                for p in print_me:
                    f.write(json.dumps(p, indent=2))
        # save OS query in ./tests
        else:
            with open('tests/' + query_str + '-expected.json', 'w') as f:
                f.write(json.dumps(print_me, indent=2))

    # export OPENSEARCH_PRINT="debug" to print to command line
    elif os.getenv('OPENSEARCH_PRINT') == 'debug':
        print('\n',place)
        if query_str:
            print(query_str)
        if isinstance(print_me, list):
            for p in print_me:
                print(json.dumps(p, indent=2))
        else:
            print(json.dumps(print_me, indent=2))


@app.route('/autosuggest', methods=['POST', 'GET'])
def autosuggest(test_json=None):
    data = request.json if not test_json else test_json
    #print('autosuggest 1', json.dumps(data))

    # handle scope if it is None, [] or [""]
    scope = data.get('scope', ['all'])
    if not scope[0]:
        scope = ['all']

    query_str = data['query'].strip()
    is_tibetan = bool(re.search(r'[\u0F00-\u0FFF]', query_str))
    query_str, query_str_bo = convert_tibetan(query_str)
    query_str = re.sub("[‘’‛′‵ʼʻˈˊˋ`]", "'", query_str)

    # id in autosuggest
    if re.search(r'([^\s0-9]\d)', query_str):
        os_json = id_json_autosuggest(query_str, scope)
        r = do_search(os_json, 'bdrc_prod')
        results = []
        for hit in r['hits']['hits']:
            labels = []
            for field, value in hit['_source'].items():
                if field.startswith('prefLabel'):
                    labels.append(value[0].strip())
            results.append({'lang': hit['_source'].get('lang'), 'res': query_str + ' ' + '; '.join(labels)})
            #result.append(query_str + ' ' + '; '.join(labels))
        return results if not test_json else os_json

    # normal
    os_json = autosuggest_json(query_str, scope)
    #print(json.dumps(os_json, indent=4))
    r = do_search(os_json, 'bdrc_autosuggest')

    if 'error' in r:
        print('Error in query:', json.dumps(os_json, indent=4))
        print('----')
        print('Opensearch error:', r)
        return []

    results = []
    hits = r['suggest']['autocomplete'][0]['options']
    for hit in hits:
        if is_tibetan:
            suggestion = CONVERTER.toUnicode(hit['text'])
        else:
            suggestion = suggestion_highlight(query_str, hit['text'])
        results.append({'lang': hit['_source'].get('lang'), 'res': suggestion})
    #print(results)

    #print('autosuggest 2', json.dumps(os_json))
    return results if not test_json else os_json

def in_etext_search(data):
    # search in the right language
    query_string_ascii, query_string_bo = get_query_str(data['query'])
    if data['lang'] == 'en':
        query_field = "chunks.text_en"
        query_str = query_string_ascii
    elif data['lang'] == 'bo' or data['lang'] == 'bo_x_ewts':
        query_field = "chunks.text_bo"
        query_str = query_string_bo

    # select the doc(s)
    if data.get('etext_instance'):
        doc_selector = {"term": {"etext_instance": data['etext_instance']}}
    elif data.get('etext_vol'):
        doc_selector = {"term": {"etext_vol": data['etext_vol']}}
    elif data.get('id'):
        doc_selector = {"term": {"_id": data['id']}}
    elif data.get('_id'):
        doc_selector = {"term": {"_id": data['_id']}}

    # build the json
    os_json = {
        "size": 10000,
        "_source": ["volumeNumber", "etextNumber", "etext_vol", "etext_pages"],
        "sort": [
            {
                "volumeNumber": {
                    "order": "asc"
                }
            },
            {
                "etextNumber": {
                    "order": "asc"
                }
            }
        ],
        "query": {
            "constant_score": {
                "filter": {
                    "bool": {
                        "must": [
                            doc_selector,
                            {
                                "nested": {
                                    "path": "chunks",
                                    "query": {
                                        "bool": {
                                            "must": [
                                                {
                                                    "match_phrase": {query_field: query_str}
                                                }
                                            ]
                                        }
                                    },
                                    "inner_hits": {
                                        "_source": {
                                            "includes": ["chunks.cstart", "chunks.cend"]
                                        },
                                        "size": 100,
                                        "highlight": {
                                            "fields": {
                                                query_field: {
                                                    "number_of_fragments": 0,
                                                    "fragment_size": 0,
                                                    "type": "plain"                 
                                                }
                                            }
                                        },
                                        "sort": [
                                            {
                                                "chunks.cstart": {
                                                    "order": "asc"
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
    }

    #print(json.dumps(os_json, indent=2))
    r = do_search(os_json, 'bdrc_prod')
    if 'error' in r:
        print('Error in query:', json.dumps(os_json, indent=4))
        print('----')
        print('Opensearch error:', r)

    hits = []
    for doc in r['hits']['hits']:
        for hit in doc['inner_hits']['chunks']['hits']['hits']:
            combined_snippets = 0
            chunk = re.sub('<(/?)em>', r'<\1EM>', hit['highlight'][query_field][0])

            # combine tokens of a highlight
            chunk = re.sub('</EM>(.{0,5})<EM>', r'\1', chunk, flags=re.DOTALL)

            # work around an Opensearch bug, which omits highlights at the beginning of a field
            chunk = re.sub('^'+query_str, '<EM>'+query_str+'</EM>', chunk)

            # loop through <em> tags in a chunk
            positions = [len(x) for x in re.split('</?EM>', chunk)]
            for n in range(1, len(positions) - 1, 2):

                # Find the page(s) for the match
                # page.cstart is the absolute page start
                # hit.cstart is the absolute chunk start                
                abs_match_start = hit['_source']['cstart'] + sum(positions[:n])
                abs_match_end = hit['_source']['cstart'] + sum(positions[:n+1])
                start_page_obj = next((page for page in doc['_source']['etext_pages'] if page['cstart'] <= abs_match_start <= page['cend']), None)
                end_page_obj = next((page for page in doc['_source']['etext_pages'] if page['cstart'] <= abs_match_end <= page['cend']), None)

                # normal case
                if not combined_snippets:
                    # create a snippet
                    obj = re.search('(.{0,50}<EM>.+?</EM>.{0,50})', chunk, flags=re.DOTALL)
                    if obj:
                        snippet = obj.group(1)
                        # main snippet back to lower case
                        snippet = re.sub('EM>', 'em>', snippet, count=2)

                        # check for multiple matches in one snippet
                        # full tags
                        snippet, combined_snippets = re.subn('<EM>(.*?)</EM>', r'<em>\1</em>', snippet)
                        # incomplete or broken tags at the end
                        snippet = re.sub('<E.*$', '', snippet)
                        # incomplete or broken tags in the beginning `em>text </em>`
                        snippet = re.sub('^[^<]*</em>', '', snippet)
                        #`/em>` in the beginning
                        snippet = re.sub('^[^<]*m>', '', snippet)
                        # `>` in the beginning
                        snippet = re.sub('^>', '', snippet)

                        # mark this snippet done
                        chunk = re.sub('<EM>', '<em>', chunk, count = combined_snippets + 1)
                        chunk = re.sub('</EM>', '</em>', chunk, count = combined_snippets + 1)

                        # tidy up both ends of the snippet
                        if data['lang'] == 'bo':
                            snippet = re.sub('^.{0,5}[་།༔༑༄༅༴༶༸༺༻༼༽༾༿༊་༈༉༒ ་]', '', snippet)
                            snippet = re.sub('([་།༔༑༄༅༴༶༸༺༻༼༽༾༿༊་༈༉༒ ་]).{0,5}$', r'\1', snippet)
                        else:
                            snippet = re.sub('^.{0,5}\s', '', snippet)
                            snippet = re.sub('\s.{0,5}$', '', snippet)
                        snippet = '…' + snippet + '…'
                    else:
                        snippet = None

                # previous snippet contained more than one matches, including this one
                else:
                    combined_snippets -= 1
                    snippet = None

                hits.append({
                    'etextId': doc['_id'],
                    'etextNumber': doc['_source']['etextNumber'],
                    'volumeId': doc['_source'].get('etext_vol'),
                    'volumeNumber': doc['_source']['volumeNumber'],
                    'startPnum': start_page_obj['pnum'],
                    'startPageCstart':  start_page_obj['cstart'],
                    'endPnum': end_page_obj['pnum'],
                    'highlightStart': abs_match_start - start_page_obj['cstart'],
                    'highlightEnd': abs_match_end - end_page_obj['cstart'],
                    'snippet': snippet
                })
                
    return hits

# search within etext
@app.route('/in_etext', methods=['POST', 'GET'])
def in_etext(test_json=None):
    data = request.json if not test_json else test_json
    result = in_etext_search(data)
    return result

# normal msearch
@app.route('/msearch', methods=['POST', 'GET'])
def msearch(test_json=None):
    ndjson = request.data.decode('utf-8') if not test_json else test_json
    original_jsons = []
    for query in ndjson.split('\n')[:-1]:
        original_jsons.append(json.loads(query))

    query_str, query_str_bo = get_query_str(original_jsons[1])

    # create tests or debug
    print_jsons(original_jsons, 'original jsons from searchkit', query_str)

    # id search
    if re.search(r'([^\s0-9]\d)', query_str):
        data = id_json_search(query_str, original_jsons)
        results = do_msearch(data, 'bdrc_prod')
        return results if not test_json else data

    # etext only
    elif is_etext_only(original_jsons):
        big_query = etext_json(query_str, query_str_bo)
        data = replace_bdrc_query(original_jsons, big_query)
        data = remove_etext_filter(data)

    # AND search
    elif re.search('[^A-Z]AND[^A-Z]', query_str):
        big_query = and_json(query_str, query_str_bo)
        data = replace_bdrc_query(original_jsons, big_query)

    # normal search
    else:
        big_query = big_json(query_str, query_str_bo)
        data = replace_bdrc_query(original_jsons, big_query)

    print_jsons(data, 'json to opensearch')
    results = do_msearch(data, 'bdrc_prod')

    if 'error' in results:
        print('Error in query:', json.dumps(data, indent=4))
        print('----')
        print('Opensearch error:', results)
    
    return results if not test_json else data

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
