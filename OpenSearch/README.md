# autocomplete-prototype/OpenSearch

### Updated files
- `search_bdrc.py` has both autosuggest and search
- `indexer-autosuggest.py` replaces `remote-indexer-autocomplete.py`

### ENV variables 
The scripts expect the env variables OPENSEARCH_URL, OPENSEARCH_USER and OPENSEARCH_PASSWORD. 
The URL is https://opensearch.bdrc.io

### Debug
If you `export OPENSEARCH_PRINT="tests"` and create `./tests/` under the script directory, it will log three JSON files at each query:

- JSON from searchkit
- JSON to Opensearch
- Result JSON

### Run

`python3 search_bdrc.py`

### /autosuggest

Input (POST or GET):

```json
{
  "query": "skyes rabs kyi sa b"
}
```

output:

```json
[
  {
    "lang": "bo_x_ewts",
    "res": "skyes rabs kyi sa b<suggested>cad</suggested>"
  }
]
```

### /search

Input is any opensearch query.

Output is the usual opensearch output.

The API modifies the opensearch query in the following way:
- for IP addresses in China, it filters on document with the field `"ric"` not set to `true`
- It replaces the object "bdrc-query" by a custom query.

For example

```json
GET bdrc_prod/_search
{
  "from": 0,
  "size": 10,
  "aggs": {
    "type": {
      "terms": {
        "field": "type"
      }
    }
  },
  "highlight": {
    "fields": {
      "prefLabel_bo_x_ewts": {},
      "altLabel_bo_x_ewts": {},
      "seriesName_bo_x_ewts": {},
      "seriesName_en": {}
    }
  },
  "query": {
    "function_score": {
      "script_score": {
        "script": {
          "id": "bdrc-score"
        }
      },
      "query": {
        "bdrc-query": "dpe bsdur ma"
      }
    }
  }
}
```
#### Modified query
```
{
    "from": 0,
    "size": 10,
    "aggs": {
        "type": {
            "terms": {
                "field": "type"
            }
        }
    },
    "highlight": {
        "fields": {
            "prefLabel_bo_x_ewts": {},
            "altLabel_bo_x_ewts": {},
            "seriesName_bo_x_ewts": {},
            "seriesName_en": {}
        }
    },
    "query": {
        "function_score": {
            "script_score": {
                "script": {
                    "id": "bdrc-score"
                }
            },
            "query": {
                "dis_max": {
                    "queries": [
                        {
                            "bool": {
                                "must": [
                                    {
                                        "multi_match": {
                                            "type": "phrase",
                                            "query": "dpe bsdur ma",
                                            "fields": [
                                                "altLabel_bo_x_ewts^0.6",
                                                "altLabel_en^0.6",
                                                "authorshipStatement_bo_x_ewts^0.005",
                                                "authorshipStatement_en^0.005",
                                                "comment^0.0001",
                                                "comment_bo_x_ewts^0.0001",
                                                "comment_en^0.0001",
                                                "prefLabel_bo_x_ewts^1",
                                                "prefLabel_en^1",
                                                "publisherLocation_bo_x_ewts^0.01",
                                                "publisherLocation_en^0.01",
                                                "publisherName_bo_x_ewts^0.01",
                                                "publisherName_en^0.01",
                                                "seriesName_bo_x_ewts^0.1",
                                                "seriesName_en^0.1"
                                            ]
                                        }
                                    }
                                ],
                                "boost": 1.1
                            }
                        },
                        {
                            "bool": {
                                "must": [
                                    {
                                        "multi_match": {
                                            "type": "phrase",
                                            "query": "dpe",
                                            "fields": [
                                                "altLabel_bo_x_ewts^0.6",
                                                "altLabel_en^0.6",
                                                "authorshipStatement_bo_x_ewts^0.005",
                                                "authorshipStatement_en^0.005",
                                                "comment^0.0001",
                                                "comment_bo_x_ewts^0.0001",
                                                "comment_en^0.0001",
                                                "prefLabel_bo_x_ewts^1",
                                                "prefLabel_en^1",
                                                "publisherLocation_bo_x_ewts^0.01",
                                                "publisherLocation_en^0.01",
                                                "publisherName_bo_x_ewts^0.01",
                                                "publisherName_en^0.01",
                                                "seriesName_bo_x_ewts^0.1",
                                                "seriesName_en^0.1"
                                            ]
                                        }
                                    },
                                    {
                                        "multi_match": {
                                            "type": "phrase",
                                            "query": "bsdur ma",
                                            "fields": [
                                                "altLabel_bo_x_ewts^0.6",
                                                "altLabel_en^0.6",
                                                "authorshipStatement_bo_x_ewts^0.005",
                                                "authorshipStatement_en^0.005",
                                                "comment^0.0001",
                                                "comment_bo_x_ewts^0.0001",
                                                "comment_en^0.0001",
                                                "prefLabel_bo_x_ewts^1",
                                                "prefLabel_en^1",
                                                "publisherLocation_bo_x_ewts^0.01",
                                                "publisherLocation_en^0.01",
                                                "publisherName_bo_x_ewts^0.01",
                                                "publisherName_en^0.01",
                                                "seriesName_bo_x_ewts^0.1",
                                                "seriesName_en^0.1"
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "bool": {
                                "must": [
                                    {
                                        "multi_match": {
                                            "type": "phrase",
                                            "query": "dpe bsdur",
                                            "fields": [
                                                "altLabel_bo_x_ewts^0.6",
                                                "altLabel_en^0.6",
                                                "authorshipStatement_bo_x_ewts^0.005",
                                                "authorshipStatement_en^0.005",
                                                "comment^0.0001",
                                                "comment_bo_x_ewts^0.0001",
                                                "comment_en^0.0001",
                                                "prefLabel_bo_x_ewts^1",
                                                "prefLabel_en^1",
                                                "publisherLocation_bo_x_ewts^0.01",
                                                "publisherLocation_en^0.01",
                                                "publisherName_bo_x_ewts^0.01",
                                                "publisherName_en^0.01",
                                                "seriesName_bo_x_ewts^0.1",
                                                "seriesName_en^0.1"
                                            ]
                                        }
                                    },
                                    {
                                        "multi_match": {
                                            "type": "phrase",
                                            "query": "ma",
                                            "fields": [
                                                "altLabel_bo_x_ewts^0.6",
                                                "altLabel_en^0.6",
                                                "authorshipStatement_bo_x_ewts^0.005",
                                                "authorshipStatement_en^0.005",
                                                "comment^0.0001",
                                                "comment_bo_x_ewts^0.0001",
                                                "comment_en^0.0001",
                                                "prefLabel_bo_x_ewts^1",
                                                "prefLabel_en^1",
                                                "publisherLocation_bo_x_ewts^0.01",
                                                "publisherLocation_en^0.01",
                                                "publisherName_bo_x_ewts^0.01",
                                                "publisherName_en^0.01",
                                                "seriesName_bo_x_ewts^0.1",
                                                "seriesName_en^0.1"
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    }
}
```
### Index autosuggest

Creates the autosuggest index.  Deletes the old one. Takes the data directly from `bdrc_prod`
`python3 indexer-autosuggest.py`
