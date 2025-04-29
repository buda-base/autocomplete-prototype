import json, re, requests
from requests.auth import HTTPBasicAuth
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import jsonlines
import io
# suppress redundant messages in local
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging


from pyewts import pyewts
CONVERTER = pyewts()

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains on all routes

class NonASCIIJSONEncoder(json.JSONEncoder):
    def __init__(self, **kwargs):
        kwargs['ensure_ascii'] = False
        super(NonASCIIJSONEncoder, self).__init__(**kwargs)

app.json_encoder = NonASCIIJSONEncoder

# we only return a certain number of hits per etext in the general search
INNER_HITS_SIZE = 3

# allow missing tokens every SLOP_VALUE tokens
SLOP_VALUE = 6

# 715 exact year ranked on top
# 700 matches 8th century ranked lowest
# associatedCentury, birthDate, deathDate, flourishedDate, publicationDate
def parse_year(query_str): 
    # Find all 3-4 digit numbers bounded by spaces or string boundaries
    json_obj = []
    remaining_query = query_str
    
    for year in re.findall(r'(\b\d{3,4}\b)', query_str):
        year = year.strip()
        # Remove the year from remaining query
        remaining_query = remaining_query.replace(year, '').strip()
        
        year_num = int(year)
        shoulds = [
            {"term": {"birthDate": {"value": year_num, "boost": 3.0}}},
            {"term": {"deathDate": {"value": year_num, "boost": 3.0}}},
            {"term": {"publicationDate": {"value": year_num, "boost": 3.0}}},
        ]
        if year.endswith('00'):
            century = year_num // 100 + 1
            shoulds.append({"term": {"associatedCentury": {"value": century, "boost": 0.7}}})

        json_obj.append({
            "bool": {
                "should": shoulds,
                "minimum_should_match": 1
            }
        })


    return json_obj, remaining_query

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

def get_fields(structure, langs=['bo_x_ewts', 'en', 'hani', 'iast', 'mymr', 'khmr']):
    # if more than two languages, the two-phrase match starts reducing phrase pairs to avoid too big queries, and search suffers
    all_fields = {
        "prefLabel_hani": 1, "prefLabel_mymr": 1, "prefLabel_khmr": 1, "prefLabel_iast": 1, "prefLabel_bo_x_ewts": 1, "prefLabel_en": 0.25, 
        "prefLabel_bo_x_ewts.ewts-phonetic": 0.95, "prefLabel_bo_x_ewts.english-phonetic": 0.95,
        "etext_prefLabel_bo_x_ewts": 1, "etext_prefLabel_en": 0.25, 
        "authorName_bo_x_ewts": 0.7, "authorName_en": 0.15, "authorName_hani": 0.7, "authorName_iast": 0.7, "authorName_mymr": 0.7, "authorName_khmr": 0.7,
        "authorName_bo_x_ewts.ewts-phonetic": 0.65, "authorName_bo_x_ewts.english-phonetic": 0.62, 
        "altLabel_bo_x_ewts": 1, "altLabel_en": 0.25, "altLabel_hani": 1, "altLabel_iast": 1, "altLabel_mymr": 1, "altLabel_khmr": 1, 
        "altLabel_bo_x_ewts.ewts-phonetic": 0.95, "altLabel_bo_x_ewts.english-phonetic": 0.95,
        "summary_bo_x_ewts": 0.1, "summary_en": 0.1, "summary_hani": 0.1, 
        "seriesName_bo_x_ewts": 0.05, "seriesName_en": 0.05, 
        "publisherName_bo_x_ewts": 0.01, "publisherLocation_bo_x_ewts": 0.01, "publisherName_en": 0.01, "publisherLocation_en": 0.01, "publisherName_hani": 0.01, "publisherLocation_hani": 0.01, 
        "etext_publisherName_bo_x_ewts": 0.01, "etext_publisherLocation_bo_x_ewts": 0.01, "etext_publisherName_en": 0.01, "etext_publisherLocation_en": 0.01, 
        "authorshipStatement_bo_x_ewts": 0.1, 
        "authorshipStatement_bo_x_ewts.ewts-phonetic": 0.095, "authorshipStatement_bo_x_ewts.english-phonetic": 0.095,
        "comment_bo_x_ewts": 0.02, "comment_en": 0.02, "comment_hani": 0.02
    }

    # select the fields of selected languages
    fields = {k: v for k, v in all_fields.items() if any(f'_{lang}' in k for lang in langs)}

    if structure == 'with_weights':
        return [f'{name}^{weight}' for name, weight in list(fields.items())]
    elif structure == 'exact_with_weights':
        exact_fields = {}
        for name, weight in fields.items():
            if '.' in name and '_bo' in name:
                continue
            if '_bo' in name:
                name = name + '.exact'
            exact_fields[name] = weight
        return [f'{name}^{weight}' for name, weight in list(exact_fields.items())]
    elif structure == 'bo_exacts':
        exact_fields = {}
        for name, weight in fields.items():
            if '.' in name and '_bo' in name:
                continue
            if '_bo' in name:
                name = name + '.exact'
            exact_fields[name] = weight
        return list(fields.keys())
    elif structure == 'for_autosuggest_highlight':
        return {key: {} for key in list(fields.keys())}
    elif structure == 'as_list':
        return list(fields.keys())
    elif structure == 'as_dict':
        return dict(list(fields.items()))
    
def and_json(query_str, query_str_bo):
    # double quotes split
    exact_phrases = []
    exact_phrases_bo = []
    if re.search('".+"', query_str):
        exact_phrases = re.findall(r'"(.*?\S+?.*?)"', query_str)
        query_str = re.sub('".+"', ' AND ', query_str)
        exact_phrases_bo = re.findall('"(.*?[\u0F00-\u0FFF]+?.*?)"', query_str_bo)
        query_str_bo = re.sub('".+"', 'AND', query_str_bo)

    # AND split
    phrases = re.split(' AND ', query_str)
    phrases_bo = re.split('AND', query_str_bo)

    fields = get_fields('with_weights')
    exact_fields = get_fields('exact_with_weights')

    must = []

    # Remove empty phrases and whitespace-only phrases
    phrases = [p for p in phrases if p.strip()]
    phrases_bo = [p for p in phrases_bo if p.strip()]
    exact_phrases = [p for p in exact_phrases if p.strip()]
    exact_phrases_bo = [p for p in exact_phrases_bo if p.strip()]

    # phrases outside of double quotes
    for n in range(0, min(len(phrases), len(phrases_bo))):
        should = []

        # match metadata
        should.append({"multi_match": {"query": phrases[n], "fields": fields, "type": "phrase", "boost": 2.0}})

        # match etext
        should.append(etext_json(phrases[n], phrases_bo[n], names=True, source=True, exact=True))

        # append shoulds of each phrase to must, which produces the AND
        must.append({"bool": {"should": should}})

    # phrases inside double quotes
    for n in range(0, min(len(exact_phrases), len(exact_phrases_bo))):
        should = []

        # match metadata
        should.append({"multi_match": {"query": exact_phrases[n], "fields": exact_fields, "type": "phrase", "boost": 2.0}})

        # match etext
        should.append(etext_json(exact_phrases[n], exact_phrases_bo[n], names=True, source=True, exact=True))

        # append shoulds of each phrase to must, which produces the AND
        must.append({"bool": {"should": should}})

    json_obj = {
        "bool": {
            "must": must
        }
    }

    return json_obj, highlight_json(phrases, exact=exact_phrases)

def big_json(query_str, query_str_bo, omit_two_phrase=False, omit_etext=False):
    year_json, query_str = parse_year(query_str)
    query_words = re.split(r'[ \-/_]+', query_str)
    number_of_tokens = len(query_words)
    if query_str.strip():
        dis_max = [{'dis_max': {'queries': []}}]
    else:
        dis_max = []

    big_query = {
        "bool": {
            "must": dis_max + year_json
        }
    }

    # highlight strings is for rebuilding the highlight query
    highlight_strings = [query_str]

    # 1. full phrase match
    weight_fields = get_fields('with_weights')
    should = {
        'bool': {
            'must': [
                {
                    'multi_match': {
                        'type': 'phrase', 
                        'query': query_str, 
                        'fields': weight_fields,
                        'slop': int(number_of_tokens/SLOP_VALUE)
                    }
                }
            ],
            'boost': 1.1
        }
    }
    if query_str.strip():
        big_query['bool']['must'][0]['dis_max']['queries'].append(should)

        # 2. etext full match
        if not omit_etext:
            big_query['bool']['must'][0]['dis_max']['queries'].append(etext_json(query_str, query_str_bo))

        # 3. create all two-phrase combinations of the keywords
        if number_of_tokens > 1 and not omit_two_phrase:
            # Define cut points to start in the middle, to exclude the shortest phrases if we need to exclude something to keep clauses under 1024
            cuts = []
            for n in range(0, int(number_of_tokens/2 + 1)):
                if not n:
                    cuts.append(int(number_of_tokens/2))
                else:
                    for lr in [-1,1]:
                        cut = int(number_of_tokens/2) + n * lr
                        if cut > 0 and cut < number_of_tokens:		
                            cuts.append(cut)
            for cut in cuts:
                # Ajust below to avoid too many clauses error in Opensearch.
                # (If clauses are still too many, two-phrase query will be omittedaltogether.)
                if len(big_query['bool']['must'][0]['dis_max']['queries']) < 18 - number_of_tokens * 0.9:
                    phrase1 = ' '.join(query_words[:cut]) # mi
                    phrase2 = ' '.join(query_words[cut:]) # la ras pa
                    if phrase2 in ["tu", "du", "su", "gi", "kyi", "gyi", "gis", "kyis", "gyis", "kyang", "yang", "ste", "de", "te", "go", "ngo", "do", "no", "bo", "ro", "so", "'o", "to", "pa", "ba", "gin", "kyin", "gyin", "yin", "c'ing", "zh'ing", "sh'ing", "c'ig", "zh'ig", "sh'ig", "c'e'o", "zh'e'o", "sh'e'o", "c'es", "zh'es", "pas", "pa'i", "pa'o", "bas", "ba'i", "la"]:
                        continue
                    # Collect phrase pairs in two should queries, and put the two groups inside a must query
                    must = []
                    for phrase in [phrase1, phrase2]:
                        must.append ({
                            "bool": {
                                "should": [
                                    {
                                        "multi_match": {
                                            "type": "phrase",
                                            "query": phrase,
                                            "fields": get_fields('with_weights', ['bo_x_ewts'])
                                        }
                                    }#,
                                    # Uncomment to include etext in two-phrase query. This was commented out because of latency.
                                    #etext_json(phrase, CONVERTER.toUnicode(phrase), names=True, source=True)
                                ]
                            }
                        })
                        highlight_strings.append(phrase)
                    big_query['bool']['must'][0]['dis_max']['queries'].append({'bool': {'must': must, 'boost': 0.2}})
    highlight_query = highlight_json(highlight_strings)
    return big_query, highlight_query


def highlight_json(highlight_strings, exact=[]):
    should = []
    fields = get_fields('as_list')
    if exact:
        fields += get_fields('bo_exacts')
    for string in highlight_strings + exact:
        should.append({
            "multi_match": {
                "type": "phrase", 
                "query": string, 
                "fields": fields,
                "slop": int(len(re.split(r'[ \-/_]+', string)) / SLOP_VALUE)
            }
        })

    highlight_query = {
        "highlight_query": {
            "bool": {"should": should}
        },
        "fields": {
            "*": {},
            "*Label*": {"number_of_fragments": 0}
        }
    }
    return highlight_query

def range_workaround_before_os(ndjson):
    for json_obj in ndjson:
        if 'aggs' in json_obj:
            aggs = json_obj['aggs']
            for field_name, field_config in aggs.items():
                if isinstance(field_config, dict) and 'range' in field_config:
                    # Convert range aggregations to filter aggregations
                    ranges = field_config['range']['ranges']
                    filters = {}
                    for r in ranges:
                        from_val = r.get('from', '*')
                        to_val = r.get('to', '*')
                        # Convert numbers to float format
                        if isinstance(from_val, (int, float)):
                            from_val = f"{float(from_val)}"
                        if isinstance(to_val, (int, float)):
                            to_val = f"{float(to_val)}"
                        filter_name = f"range_{from_val}_{to_val}"
                        filters[filter_name] = {
                            "range": {
                                field_name.replace('range_', ''): {
                                    k: v for k, v in r.items() if k in ['from', 'to']
                                }
                            }
                        }
                    json_obj['aggs'][field_name] = {
                        "filters": {
                            "filters": filters
                        }
                    }
    return ndjson

def range_workaround_after_os(results):
    for response in results.get('responses', []):
        for agg in response.get('aggregations', {}):
            if 'buckets' in response['aggregations'][agg]:
                if isinstance(response['aggregations'][agg]['buckets'], dict):
                    old_buckets = response['aggregations'][agg]['buckets']
                    new_buckets = []
                    for bucket in old_buckets:
                        key_groups = re.search(r'range_([\d.]+)_([\d.]+)', bucket)
                        from_key = key_groups.group(1)
                        to_key = key_groups.group(2)
                        if key_groups:
                            new_bucket = {
                                'key': from_key + '-' + to_key,
                                'from': float(from_key), 
                                'to': float(to_key), 
                                'doc_count': old_buckets[bucket]['doc_count']
                            }
                            new_buckets.append(new_bucket)
                    if new_buckets:
                        response['aggregations'][agg]['buckets'] = sorted(new_buckets, key=lambda x: x['from'])
    return results

def modify_highlights(results):
    # Get the best prefLabel highlights
    if 'responses' in results:
        for hit in results['responses'][0]['hits']['hits']:
            if 'highlight' in hit:
                combined_highlight = {}

                # combine lenient highlight fields to the main one
                for mainfield in ['prefLabel_bo_x_ewts', 'altLabel_bo_x_ewts', 'authorName_bo_x_ewts', 'authorshipStatement_bo_x_ewts']:
                    combined_values = hit['highlight'].get(mainfield , []) + \
                        hit['highlight'].get(mainfield + '.ewts-phonetic', []) + \
                        hit['highlight'].get(mainfield + '.english-phonetic', [])
                    if combined_values:
                        hit['highlight'][mainfield] = combined_values
                    if mainfield + '.ewts-phonetic' in hit['highlight']:
                        del hit['highlight'][mainfield + '.ewts-phonetic']
                    if mainfield + '.english-phonetic' in hit['highlight']:
                        del hit['highlight'][mainfield + '.english-phonetic']

                # Select the best prefLabel highlight
                if 'prefLabel_bo_x_ewts' in hit['highlight']:
                    pref_label_ems = set()
                    for subfield in hit['highlight']['prefLabel_bo_x_ewts']:
                        these_ems = set(re.findall('<em>(.*?)</em>', subfield))
                        if len(these_ems) > len(pref_label_ems):
                            pref_label_ems = these_ems
                            pref_label_highlight = subfield
                    hit['highlight']['prefLabel_bo_x_ewts'] = [pref_label_highlight]

                    # Find fields with the most different tokens than in the prefLabel
                    for field, values in hit['highlight'].items():
                        if field !='prefLabel_bo_x_ewts':
                            most_unique = -1
                            for value in values:
                                these_ems = set(re.findall('<em>(.*?)</em>', value))
                                unique_ems = these_ems - pref_label_ems
                                if len(unique_ems) > most_unique:
                                    most_unique = len(unique_ems)
                                    most_unique_value = value
                            hit['highlight'][field] = [most_unique_value]

                # Check that a tiny match in metadata does not prevent a perfect etext match from highlights
                # count tokens in the main highlight
                if "highlight" in hit and 'inner_hits' in hit and 'etext' in hit['inner_hits']:
                    metadata_tokens_qty = 0
                    for metadata_field in hit['highlight']:
                        for metadata in hit['highlight'][metadata_field]:
                            tokens_qty = len(re.findall('<em>', metadata))
                            if tokens_qty > metadata_tokens_qty:
                                metadata_tokens_qty = tokens_qty
                        # count tokens in the etext highlight
                    for etext_hit in hit['inner_hits']['etext']['hits'].get('hits', []):
                        if 'inner_hits' in etext_hit and 'chunks' in etext_hit['inner_hits']:
                            for chunk_hit in etext_hit['inner_hits']['chunks']['hits'].get('hits', []):
                                for highlight_field in chunk_hit.get('highlight', []):

                                    # work around opensearch bug
                                    if len(chunk_hit['highlight'][highlight_field]) == 2 and chunk_hit['highlight'][highlight_field][0].endswith('</em>'):
                                        chunk_hit['highlight'][highlight_field] = [''.join(chunk_hit['highlight'][highlight_field])]

                                    for etext_highlight in chunk_hit['highlight'][highlight_field]:
                                        etext_tokens_qty = len(re.findall('<em>', chunk_hit['highlight'][highlight_field][0]))
                                        # delete the main highlight if etext matches much better
                                        if etext_tokens_qty * 0.8 >= metadata_tokens_qty and "highlight" in hit:
                                            del hit['highlight']
                                            break
    
    return results

def etext_json(query_str, query_str_bo, names=False, source=True, exact=False):
    if source:
        child_source = {"includes": ["etext_instance", "etext_pagination_in", "etext_imagegroup", "etext_vol", "volumeNumber"]}
    else:
        child_source = False
    if exact:
        exact_field = '.exact'
    else:
        exact_field = ''

    json_obj = {
        "bool": {
            "must": [
                {
                    "has_child": {
                        "type": "etext",
                        "score_mode": "none",
                        "query": {
                            "nested": {
                                "path": "chunks",
                                "score_mode": "none",
                                "query": {
                                    "bool": {
                                        "should": [
                                            {
                                                "match_phrase": {
                                                    "chunks.text_bo" + exact_field: query_str_bo
                                                }
                                            },
                                            {
                                                "match_phrase": {
                                                    "chunks.text_en": query_str
                                                }
                                            },
                                            {
                                                "match_phrase": {
                                                    "chunks.text_hani": query_str
                                                }
                                            }
                                        ]
                                    }
                                },
                                "inner_hits": {
                                    "_source": source,
                                    "highlight": {
                                        "fields": {
                                            "chunks.text_bo" + exact_field: {
                                                "highlight_query": {
                                                    "match_phrase": {
                                                        "chunks.text_bo" + exact_field: query_str_bo
                                                    }
                                                }
                                            },
                                            "chunks.text_en": {
                                                "highlight_query": {
                                                    "match_phrase": {
                                                        "chunks.text_en": query_str
                                                    }
                                                }
                                            },
                                            "chunks.text_hani": {
                                                "highlight_query": {
                                                    "match_phrase": {
                                                        "chunks.text_hani": query_str
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
                            "_source": child_source,
                            "highlight": {
                                "fields": {
                                    "chunks.text_bo" + exact_field: {
                                        "highlight_query": {
                                            "match_phrase": {
                                                "chunks.text_bo" + exact_field: query_str_bo
                                            }
                                        }
                                    },
                                    "chunks.text_en": {
                                        "highlight_query": {
                                            "match_phrase": {
                                                "chunks.text_en": query_str
                                            }
                                        }
                                    },
                                    "chunks.text_hani": {
                                        "highlight_query": {
                                            "match_phrase": {
                                                "chunks.text_hani": query_str
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }
    }
    if names:
        json_obj['bool']['must'][0]['has_child']['inner_hits']['name'] = query_str
    
    if not source:
        json_obj['bool']['must'][0]['has_child']['inner_hits']['_source'] = 'false'        


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
        "_source": {
            "excludes": ["etext_pages", "chunks"]
        },
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
                                },
                                {
                                    "term": {
                                        "merged": id_code
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

# Try to get highlights from all tokens of the query string, so that etext and metadata hits would be different.
# Example query: "bla mchos sa skya bka' 'bum"
def etext_highlights(results):
    if 'responses' in results:
        for hit in results['responses'][0]['hits']['hits']:
            metadata_tokens = set()
            if 'highlight' in hit:
                # 1. metadata tokens, in this case "sa skya bka' 'bum"
                for field in hit['highlight']:
                    for item in hit['highlight'][field]:
                        metadata_tokens.update(re.findall('<em>(.*?)</em>', item))
                # 2. find etext tokens that were not in metadata
                candidates = {}
                # Phrases are from two-phrase query, like "bla", "mchos sa skya bka' 'bum", "bla mchos", etc.
                for phrase, inner_hits in hit.get('inner_hits', {}).items():
                    if inner_hits['hits']['total']['value']:
                        # Store the number of tokens unique to etext, like {"bla": 1, "sa skya bka' 'bum": 0,  "bla mchos": 2}
                        etext_tokens = set(re.findall(r'\S+', phrase))
                        candidates[phrase] = len(etext_tokens - metadata_tokens)
                # Reorder the result json to have the etext-only matches first
                sorted_candidates = dict(sorted(candidates.items(), key=lambda item: (item[1], len(item[0])), reverse=True))
                temp_inner_hits = hit['inner_hits']
                ordered_inner_hits = {key: temp_inner_hits[key] for key in sorted_candidates if key in temp_inner_hits}
                hit['inner_hits'] = ordered_inner_hits
    return results

def replace_bdrc_query(original_jsons, replacement, highlight_query=None):
    for n in range(1, len(original_jsons), 2):
        # replace the main query
        try:
            if 'sort' in original_jsons[n]:
                original_jsons[n]["query"]["bool"]["must"] = [replacement]
            else:
                original_jsons[n]["query"]["function_score"]["query"]["bool"]["must"] = [replacement]
        except (KeyError, IndexError):
            print('original_jsons', original_jsons[n])
            print('replacement', replacement)

        # replace highlight
        if highlight_query:
            try: original_jsons[n]["highlight"] = highlight_query
            except: print(original_jsons[n])
    return original_jsons

def get_query_str(data):
    # prepare in-etext query string
    if isinstance(data, str):
        query_str = data
    # get query string from searchkit json
    else:
        query_str = find_string_value(data, 'query')
        if not query_str:
            return '', ''

    query_str = query_str.strip()

    query_str_ascii, query_str_bo = convert_tibetan(query_str)

    query_str_ascii = re.sub("[‘’‛′‵ʼʻˈˊˋ`]", "'", query_str_ascii)    
    query_str_ascii = re.sub('[/_]+$', '', query_str_ascii)
    query_str_ascii = stopwords(query_str_ascii)
    query_str_ascii = re.sub(r'^(t[oö]hoku|t[oö]h)[ .:]*(\d+)$', r'd\2', query_str_ascii, flags=re.IGNORECASE)

    # TODO convert 9th to 09
    # convert 9 to 09

    #print(query_str_ascii, query_str_bo)
    return query_str_ascii, query_str_bo

def is_etext_only(original_jsons):
    for one_json in original_jsons:
        if find_string_value(one_json, 'etext_search') == 'true':
            return True
    return False

def print_jsons(print_me, place, query_str):
    # export OPENSEARCH_PRINT="tests" to recreate tests
    if os.getenv('OPENSEARCH_PRINT') == 'tests':
        # save searchkit jsons in ./tests
        filename = re.sub('/', '-', query_str)
        if place == 'searchkit':
            with open('tests/' + filename + '-searchkit.json', 'w') as f:
                for p in print_me:
                    f.write(json.dumps(p, indent=2, ensure_ascii=False))
        # save OS query in ./tests
        elif place == 'opensearch':
            with open('tests/' + filename + '-opensearch.json', 'w') as f:
                f.write(json.dumps(print_me, indent=2, ensure_ascii=False))
        elif place == 'results':
            with open('tests/' + filename + '-results.json', 'w') as f:
                f.write(json.dumps(print_me, indent=2, ensure_ascii=False))

    # export OPENSEARCH_PRINT="debug" to print to command line
    elif os.getenv('OPENSEARCH_PRINT') == 'debug':
        print('\n',place)
        if query_str:
            print(query_str)
        if isinstance(print_me, list):
            for p in print_me:
                print(json.dumps(p, indent=2, ensure_ascii=False))
        else:
            print('\n________' + query_str + '________' + place + '________')
            print(json.dumps(print_me, indent=2, ensure_ascii=False))


@app.route('/autosuggest', methods=['POST', 'GET'])
def autosuggest(test_json=None):
    data = request.json if not test_json else test_json

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
        return jsonify(results) if not test_json else os_json

    # normal
    os_json = autosuggest_json(query_str, scope)
    #print(json.dumps(os_json, indent=4))
    r = do_search(os_json, 'bdrc_autosuggest')

    if 'error' in r:
        print('Error in query:', json.dumps(os_json, indent=4))
        print('----')
        print('Opensearch error:', r)
        return jsonify([])

    results = []
    hits = r['suggest']['autocomplete'][0]['options']
    for hit in hits:
        if is_tibetan:
            suggestion = CONVERTER.toUnicode(hit['text'])
        else:
            suggestion = suggestion_highlight(query_str, hit['text'])
        results.append({'lang': hit['_source'].get('lang'), 'res': suggestion})

    return jsonify(results) if not test_json else os_json

def in_etext_search(data):
    # Prepare query strings
    query_string_ascii, query_string_bo = get_query_str(data['query'])
    
    # Define the query fields
    query_fields = [
        {"match_phrase": {"chunks.text_en": query_string_ascii}},
        {"match_phrase": {"chunks.text_hani": data['query']}}
    ]

    # quotes -> exact
    exact = False
    if re.search(r'^\s*".*"\s*$', query_string_bo):
        exact = True
        query_fields.append(
            {"match_phrase": {"chunks.text_bo.exact": query_string_bo}},
        )
    else:
        query_fields.append(
            {"match_phrase": {"chunks.text_bo": query_string_bo}},
        )

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
                                            "should": query_fields,
                                            "minimum_should_match": 1
                                        }
                                    },
                                    "inner_hits": {
                                        "_source": {
                                            "includes": ["chunks.cstart", "chunks.cend"]
                                        },
                                        "size": 100,
                                        "highlight": {
                                            "fields": {
                                                "chunks.text_en": {
                                                    "number_of_fragments": 0,
                                                    "fragment_size": 0,
                                                    "type": "plain"                 
                                                },
                                                "chunks.text_hani": {
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

    fields = os_json['query']['constant_score']['filter']['bool']['must'][1]['nested']['inner_hits']['highlight']['fields']
    bo_field = 'chunks.text_bo' if not exact else 'chunks.text_bo.exact'
    fields[bo_field] = { "number_of_fragments": 0, "fragment_size": 0, "type": "plain" }
    print_jsons(os_json, 'opensearch', data['query'])

    r = do_search(os_json, 'bdrc_prod')

    print_jsons(r, 'results', data['query'])

    if 'error' in r:
        print('Error in query:', json.dumps(os_json, indent=4))
        print('----')
        print('Opensearch error:', r)

    hits = []
    for doc in r['hits']['hits']:
        for hit in doc['inner_hits']['chunks']['hits']['hits']:
            # Determine which field was matched
            matched_field = None
            for field in ['text_bo', 'text_bo.exact', 'text_en', 'text_hani']:
                if 'highlight' in hit and f'chunks.{field}' in hit['highlight']:
                    matched_field = field
                    break
            
            if not matched_field:
                logging.error("no matched field in "+str(hit))
                continue
            combined_snippets = 0
            chunk = re.sub('<(/?)em>', r'<\1EM>', hit['highlight'][f'chunks.{matched_field}'][0])

            # combine tokens of a highlight
            chunk = re.sub('</EM>(.{0,5})<EM>', r'\1', chunk, flags=re.DOTALL)

            # work around an Opensearch bug, which omits highlights at the beginning of a field
            query_str = query_string_bo if matched_field == 'text_bo' else (query_string_ascii if matched_field == 'text_en' else data['query'])
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
                        if matched_field == 'text_bo':
                            snippet = re.sub('^.{0,5}[་།༔༑༄༅༴༶༸༺༻༼༽༾༿༊་༈༉༒ ་]', '', snippet)
                            snippet = re.sub('([་།༔༑༄༅༴༶༸༺༻༼༽༾༿༊༈༉༒ ་]).{0,5}$', r'\1', snippet)
                        else:
                            snippet = re.sub(r'^.{0,5}\s', '', snippet)
                            snippet = re.sub(r'\s.{0,5}$', '', snippet)
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
                    'highlightStart': abs_match_start,
                    'highlightEnd': abs_match_end,
                    'snippet': snippet
                })
                
    return hits

def exclude_filters(data):
    for json_obj in data:
        try: filters = json_obj['query']['function_score']['query']['bool']['filter']
        except KeyError:
            try: filters = json_obj['query']['bool']['filter']
            except KeyError: continue
        for filter in filters:
            try: term = filter['bool']['should'][0]['term']
            except (KeyError, IndexError): continue
            if 'exclude_etexts' in term:
                print(filter)
                del filter['bool']['should']
                print(filter)
            if 'nocomm_search' in term:
                del filter['bool']['should']
                filter['bool']['must_not'] = [
                    {"terms": {"workGenre": ["T1491", "T304", "T2397", "T3JT5054", "T2377", "T4JW5424", "T132", "T1488", "T10MS12837"]}},
                    {"term": {"prefLabel_bo_x_ewts": "'grel"}}
                ]
    return data
    
# search within etext
@app.route('/in_etext', methods=['POST', 'GET'])
def in_etext(test_json=None):
    data = request.json if not test_json else test_json
    return in_etext_search(data)

# normal msearch
@app.route('/msearch', methods=['POST', 'GET'])
@app.route('/_msearch', methods=['POST', 'GET'])
def msearch(test_json=None, omit_two_phrase=False):
    ndjson = request.data.decode('utf-8') if not test_json else test_json
    original_jsons = []
    should_omit_etexts = False
    for query in ndjson.split('\n')[:-1]:
        if '"exclude_etexts":"true"' in query:
            should_omit_etexts = True
        original_jsons.append(json.loads(query))
    query_str, query_str_bo = get_query_str(original_jsons[1])

    # create tests or debug
    print_jsons(original_jsons, 'searchkit', query_str)

    # id search
    if re.search(r'([^\s0-9]\d)', query_str):
        data = id_json_search(query_str, original_jsons)
        print_jsons(data, 'opensearch', query_str)
        results = do_msearch(data, 'bdrc_prod')
        print_jsons(results, 'results', query_str)
        return results if not test_json else data

    # etext only
    elif is_etext_only(original_jsons):
        big_query = etext_json(query_str, query_str_bo)
        data = replace_bdrc_query(original_jsons, big_query)
        data = remove_etext_filter(data)

    # AND search and double quotes
    elif re.search('[^A-Z]AND[^A-Z]', query_str) or re.search('".*"', query_str):
        big_query, highlight_query = and_json(query_str, query_str_bo)
        data = replace_bdrc_query(original_jsons, big_query, highlight_query=highlight_query)

    # normal search
    else:
        big_query, highlight_query = big_json(query_str, query_str_bo, omit_two_phrase=omit_two_phrase, omit_etext=should_omit_etexts)
        data = replace_bdrc_query(original_jsons, big_query, highlight_query=highlight_query)


    data = exclude_filters(data)
    data = range_workaround_before_os(data)
    print_jsons(data, 'opensearch', query_str)

    results = do_msearch(data, 'bdrc_prod')

    # handle errors
    for r in results['responses']:
        if 'error' in r:
            #print('Error in query:', json.dumps(data, indent=4))
            #print('----')
            # Call this function recursively, omitting the two-phrase query
            if 'root_cause' in r['error'] and r['error']['root_cause'][0]['type'] == 'too_many_nested_clauses':
                results = msearch(omit_two_phrase=True)
                return results
            print('Opensearch error:', results)
            return(results)

    results = modify_highlights(results)
    results = range_workaround_after_os(results)

    print_jsons(results, 'results', query_str)
    return results if not test_json else data

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
    #app.run(debug=True, port=5000, host='0.0.0.0', ssl_context='adhoc')
