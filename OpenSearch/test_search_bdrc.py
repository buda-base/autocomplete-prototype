from search_bdrc import format_query
import json
import jsondiff

tests_base_paths = ["req1"]

def test_one(test_base_path):
	base = None
	expected = None
	with open('tests/'+test_base_path+'.json') as f:
	    base = json.load(f)
	with open('tests/'+test_base_path+'-expected.json') as f:
	    expected = json.load(f)
	res = format_query(base)
	diff = jsondiff.diff(res, expected, dump=True)
	if diff:
		print("ERROR: difference found in "+test_base_path+":")
		print(diff)
		print("\ngot\n")
		print(json.dumps(res))
		print("\nbut expected\n")
		print(json.dumps(expected))
	else:
		print("PASS: "+test_base_path)

def main():
	for test_base_path in tests_base_paths:
		test_one(test_base_path)

main()