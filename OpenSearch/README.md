# autocomplete-prototype/OpenSearch

### Updated files
- `search_bdrc.py` has both autosuggest and search
- `indexer-autosuggest.py` replaces `remote-indexer-autocomplete.py`

### ENV variables 
The scripts expect the env variables OPENSEARCH_URL, OPENSEARCH_USER and OPENSEARCH_PASSWORD. 
The URL is https://opensearch.bdrc.io

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
- it replaces each `"query"` object of type `bdrc-query"` by a custom query

For example

```json
GET bdrc_prod/_search
{
  "from": 0,
  "size": 0,
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
        "bdrc-api": "skyes rabs kyi sa bcad"
      }
    }
  }
}
```

### Index autosuggest

Autosuggest has been indexed, but if you want to do reindex, first download the main search index from bdrc_prod with
`python3 get-index.py > index.json`
Then index to bdrc_autosuggest with
`indexer-autosuggest.py´
This deletes the old index, creates mappings and then indexes everything.
