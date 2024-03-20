# autocomplete-prototype/OpenSearch

### Security  
The scripts expect the env variable OPENSEARCH_PW to contain the Opensearch password  
SSL has been disabled in both the indexer.py and autosuggest-flask.py.  After enabling it with OpenSearch, modify both Python files at
```
os_client = OpenSearch(
    [{'host': 'localhost', 'port': 9200}],
    http_auth=('admin', os.getenv('OPENSEARCH_PW')),
    use_ssl=False,
    verify_certs=False
)
```

### Indexing  
Copy input_ewts_categories.csv in the script directory  
python3 indexer.py

### Autosuggest Flask  
python3 autosuggest-flask.py

### Test
Open quick-demo.html in a browser and type in Wylie or Tibetan Unicode

### Develop
Data formats for input and output are the same as what is already implemented in library-dev.bdrc.io

### Example Wylie with a typo
```
{'query': 'mdo sde phax po'}
[
    {
        "category": "Topic",
        "lang": "bo-x-ewts",
        "res": "mdo sde phal po<suggested> che</suggested>"
    }
]
```
### Example Tibetan Unicode
Unicode does not use the "suggested" tags
```
{'query': 'མདོ་སྡེ་ཕལ་པོ'}
[
    {
        "category": "Topic",
        "lang": "bo",
        "res": "\u0f58\u0f51\u0f7c\u0f0b\u0f66\u0fa1\u0f7a\u0f0b\u0f55\u0f63\u0f0b\u0f54\u0f7c\u0f0b\u0f46\u0f7a"
    }
]
```
### Note
The "ignore" tag is not used 