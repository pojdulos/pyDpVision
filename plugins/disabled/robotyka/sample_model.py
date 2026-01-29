import json
import os
def get_sample_model(filename):
	try:
		model = open(filename).read()
	except FileNotFoundError:
		script_dir = os.path.dirname(os.path.abspath(__file__))
		try:
			model = open(os.path.join(script_dir, filename)).read()
		except FileNotFoundError:
			raise FileNotFoundError(f"File {filename} not found in the current directory or script directory.")
	return json.loads(model)

if __name__ == "__main__":
	m = get_sample_model('sample_model.json')
	
	for key, value in m['meta'].items():
		print(f"{key}: {value}")

	for j in m['joints']:
		print(f"Joint {j['name']}: parent={j['parent_joint']}, a={j['a']}, alpha={j['alpha']}, d={j['d']}, theta={j['theta']}")
		print(f"      type: {j['type']}, limits: {j['limits']}")

