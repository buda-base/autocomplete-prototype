from flask import Flask, json, request, make_response, send_file, jsonify
from flask_cors import CORS
import logging
from utils import get_main_script_tag
from autocomplete import auto_complete
import json

api = Flask("autosuggest")
CORS(api)

@api.route('/autosuggest', methods=['POST'])
def run_scam_api():
    """
    data should be in the form

    {
      "query": "foo"
    }
    """
    data = request.json
    query = data["query"]
    main_script_tag = get_main_script_tag(query)
    index_name = "ewts_general"
    if main_script_tag == "Tibt":
        index_name = "bo_general"
    #logging.info(index_name)
    logging.info("query: "+ query)
    res = auto_complete(query, index_name=index_name)
    return jsonify(res)

if __name__ == '__main__':
    api.run(debug=False)
