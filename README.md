# autocomplete-prototype

### Assumptions

- auto-complete starting at the beginning of results (no result where the query string starts in the middle of the result)
- some prefixes should be ignored
- there will be different indexes (for titles, person names, everything, different languages)
- the result should be a list of X (name + category), sorted using a ranking algorithm
- the source data for building an auto complete index is a list of strings with an associated category and score, the score for each string is computed separately based on the frequency of the string and possibly the entity score

### Vocabulary


Tokenization:

ཀུན་བཟང་བླ་མའི་ཞལ་ལུང -> [""]

- a full token is a token that we know is complete in the user query
- a partial token can appear as the last token of the user query if the user hasn't fully typed it