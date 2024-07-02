# autocomplete-prototype/OpenSearch

### Updated files
- `search_bdrc.py` has both autosuggest and search.  This needs to be deployed.
- `indexer-autosuggest.py` replaces `remote-indexer-autocomplete.py`.  Indexing has been done and you don't need to do that.
- `new-demo.html` replaces `quick-demo.html`, which you probably won't need but can be used for local testing.

### ENV variables 
The scripts expect the env variables OPENSEARCH_URL, OPENSEARCH_USER and OPENSEARCH_PASSWORD. 
The URL is https://opensearch.bdrc.io

### Run
`python3 search_bdrc.py`

### Autosuggest
```
https://OPENSEARCH_URL:5000/autosuggest
Input (POST or GET): {"query": "skyes rabs kyi sa b"}
Output (same as before): [{"lang": "bo_x_ewts", "res": "skyes rabs kyi sa b<suggested>cad</suggested>"}]
```
### Search
`https://OPENSEARCH_URL:5000/search`
- Input 1: raw Opensearch JSON which you send to the API instead of to OS
- Input 2: `{'query': 'skyes rabs kyi sa bcad'}`
```
Output (raw Opensearch JSON): {'took': 66, 'timed_out': False, '_shards': {'total': 1, 'successful': 1, 'skipped': 0, 'failed': 0}, 'hits': {'total': {'value': 7, 'relation': 'eq'}, 'max_score': 21.83649, 'hits': [{'_index': 'bdrc_prod', '_id': 'MW2122_361BF8', '_score': 21.83649, '_source': {'graphs': ['O01DG03'], 'scans_access': 5, 'etext_access': 3, 'prefLabel_bo_x_ewts': ['skyes rabs kyi sa bcad/'], 'type': ['PartTypeText'], 'merged': ['WA0XL5C3D2B342DD8'], 'summary_en': ["topical outline of aryasura's jatakamala"], 'language': ['LangBo'], 'author': ['P169'], 'associatedTradition': ['TraditionGeluk'], 'associatedCentury': [18], 'db_score': 0.5002899, 'db_score_in_type': 0.5002899, 'inRootInstance': ['MW2122'], 'pop_score_rk': 0.1, 'script': ['ScriptDbuCan'], 'hasSourcePrintery': ['G1PD129183'], 'printMethod': ['PrintMethod_Relief_WoodBlock'], 'inCollection': ['PR01DOR2', 'PR01JW33478', 'PRHD03'], 'firstScanSyncDate': '2016-03-30T16:20:30.571Z', 'scans_freshness': -0.008762322, 'etext_quality': 3.0, 'root_pop_score': 0.42284730076789856, 'root_pop_score_in_type': 0.42284730076789856}}, {'_index': 'bdrc_prod', '_id': 'MW3CN22341_94868B', '_score': 21.618126, '_source': {'graphs': ['O4CN10133'], 'scans_access': 5, 'etext_access': 1, 'prefLabel_bo_x_ewts': ['ja/ skyes rabs kyi sa bcad/'], 'type': ['PartTypeText'], 'merged': ['WA0XL94868B68D5DB'], 'workGenre': ['T89'], 'language': ['LangBo'], 'inRootInstance': ['MW3CN22341'], 'pop_score_rk': 0.1, 'script': ['ScriptTibt'], 'printMethod': ['PrintMethod_Relief_WoodBlock'], 'inCollection': ['PR1CTC17'], 'firstScanSyncDate': '2020-06-24T23:57:29.824Z', 'db_score': 0.5002899, 'db_score_in_type': 0.5002899, 'scans_freshness': 0.41484118, 'root_pop_score': 0.4115961194038391, 'root_pop_score_in_type': 0.4115961194038391}}, {'_index': 'bdrc_prod', '_id': 'MW3CN22341_D8BAEC', '_score': 21.618126, '_source': {'graphs': ['O4CN10133'], 'scans_access': 5, 'etext_access': 1, 'prefLabel_bo_x_ewts': ['ta/ skyes rabs kyi sa bcad/'], 'type': ['PartTypeText'], 'merged': ['WA0XLD8BAEC7D2C9D'], 'workGenre': ['T89'], 'language': ['LangBo'], 'inRootInstance': ['MW3CN22341'], 'pop_score_rk': 0.1, 'script': ['ScriptTibt'], 'printMethod': ['PrintMethod_Relief_WoodBlock'], 'inCollection': ['PR1CTC17'], 'firstScanSyncDate': '2020-06-24T23:57:29.824Z', 'db_score': 0.5002899, 'db_score_in_type': 0.5002899, 'scans_freshness': 0.41484118, 'root_pop_score': 0.4115961194038391, 'root_pop_score_in_type': 0.4115961194038391}}]}}
```
### Index autosuggest
Autosuggest has been indexed, but if you want to do reindex, first download the main search index from bdrc_prod with
`python3 get-index.py > index.json`
Then index to bdrc_autosuggest with
`indexer-autosuggest.py´
This deletes the old index, creates mappings and then indexes everything.
