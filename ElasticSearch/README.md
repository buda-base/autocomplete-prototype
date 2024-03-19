# autocomplete-prototype ElasticSearch

### Install Elasticsearch
The easiest way to install Elasticsearch on a Mac was with Docker, with the instructions at https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html

After installation
export ELASTIC_PASSWORD (step 6) and copy the http_ca.crt to the script directory (step 7)
Adding nodes or Kibana are not necessary.

### Indexing
Copy input_ewts_categories.csv in the script directory
python3 indexer.py

### Autosuggest Flask
The autosuggest API will run in port 5001
python3 autosuggest-flask.py

### Test
Open quick-demo.html in a browser and type in Wylie or Tibetan Unicode

