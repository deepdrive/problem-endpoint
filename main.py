import traceback

import constants
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
    return 'Deepdrive sim service that serves as a Botleague problem ' \
           'endpoint and CI service. ' \
           'Source https://github.com/deepdrive/deepdrive-sim-service'


@app.route('/watchdog_cron')
def watchdog_cron():
    if not request.headers['X-Appengine-Cron']:
        ret = make_error('Only App Engine may initiate cron jobs', 400)
    else:
        import watchdog
        ret = watchdog.run()
    return ret

# @app.route(constants.EVAL_TASK_ROUTE)
# def deepdrive_eval_task():
#     """Manages an eval task. This can run up to 24 hours"""
#
#     # TODO: Make task idempotent with a Firestore transaction as tasks can be
#     # fired multiple times even with max-attempts at 1
#     # kv = get_key_value_store()
#
#
#
#     payload = request.get_data(as_text=True) or '(empty payload)'
#     print('Received task with payload: {}'.format(payload))
#     return 'Printed task payload: {}'.format(payload)


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
        ret = jsonify(
            EvaluationEndpoint(problem, eval_id, eval_key, seed, docker_tag,
                               pull_request))

    except KeyError as err:
        print(traceback.format_exc())

        # If any or our required parameters were missing,
        # send a "400 Bad Request" response
        ret = make_error('the parameter {} is required'.format(err.args[0]),
                         400)

    except Exception as err:
        # If anything went wrong inside the endpoint logic,
        # send a "500 Internal Server Error" response
        print(traceback.format_exc())
        ret = make_error(err, 500)
    print(ret)
    return ret


# Run in debug mode when testing locally
if __name__ == '__main__':
    # Load our environment variables from app.yaml
    with open(os.path.join(os.path.dirname(__file__), 'app.yaml'), 'r') as f:
        config = yaml.safe_load(f)
        os.environ.update(config['env_variables'])

    # Start a Flask webserver
    app.run(host='127.0.0.1', port=8080, debug=True)
