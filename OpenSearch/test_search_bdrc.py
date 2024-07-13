from search_bdrc import normal_search
import json
import jsondiff, os, re

def test_one(test_base_path):
	base = None
	expected = None
	with open('tests/'+test_base_path+'.json') as f:
	    base = json.load(f)
	with open('tests/'+test_base_path+'-expected.json') as f:
	    expected = json.load(f)
	res = normal_search(base)
	diff = jsondiff.diff(res, expected, dump=False)
	if diff:
		print("ERROR: difference found in "+test_base_path+":")
		print(diff)
		print("\ngot\n")
		print(json.dumps(res, indent=4))
		print("\nbut expected\n")
		print(json.dumps(expected, indent=4))
	else:
		print("PASS: "+test_base_path)

def main():
	for filename in os.listdir('tests'):
		if filename.endswith('-expected.json'):
			continue
		test_one(re.sub('\.json$', '', filename))
main()