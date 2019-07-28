from EvaluationEndpoint import EvaluationEndpoint
from flask import Flask, jsonify, request
import os, yaml

# Create our Flask application
app = Flask(__name__)

# Creates a JSON error response with the specified HTTP status code
def make_error(err, code):
	response = jsonify({'error': str(err)})
	response.status_code = code
	return response

@app.route('/')
def home():
	return 'Deepdrive problem endpoint. Source https://github.com/deepdrive/problem-endpoint'

# Wire up our evaluation endpoint
@app.route('/eval/<problem>', methods=['POST'])
def endpoint(problem):
	
	try:
		
		# Unpack our endpoint parameters from the URL arguments
		eval_id = request.json['eval_id']
		eval_key = request.json['eval_key']
		seed = request.json['seed']
		docker_tag = request.json['docker_tag']
		pull_request = request.json.get('pull_request', None)

		# Run the endpoint logic
		ret = jsonify(EvaluationEndpoint(problem, eval_id, eval_key, seed, docker_tag, pull_request))

	except KeyError as err:
		
		# If any or our required parameters were missing, send a "400 Bad Request" response
		ret = make_error('the parameter {} is required'.format(err.args[0]), 400)

	except Exception as err:
		
		# If anything went wrong inside the endpoint logic, send a "500 Internal Server Error" response
		return make_error(err, 500)

# Run in debug mode when testing locally
if __name__ == '__main__':
	
	# Load our environment variables from app.yaml
	with open(os.path.join(os.path.dirname(__file__), 'app.yaml'), 'r') as f:
		config = yaml.safe_load(f)
		os.environ.update(config['env_variables'])
	
	# Start a Flask webserver
	app.run(host='127.0.0.1', port=8080, debug=True)
