import traceback

from botleague_helpers.key_value_store import get_key_value_store
from box import Box
from flask import Flask, render_template, jsonify, request
from google.cloud import firestore

import constants
from common import get_eval_jobs_kv_store
from eval_manager import EvaluationManager

app = Flask(__name__)


# Creates a JSON error response with the specified HTTP status code
def make_error(err, code):
    response = jsonify({'error': str(err)})
    response.status_code = code
    return response


@app.route("/")
def index():
    return 'Deepdrive sim service that serves as a Botleague problem ' \
           'endpoint and CI service. ' \
           'Source https://github.com/deepdrive/deepdrive-sim-service'


@app.route('/eval/<problem>', methods=['POST'])
def endpoint(problem):
    try:
        # Unpack our endpoint parameters from the URL arguments
        eval_id = request.json['eval_id']
        eval_key = request.json['eval_key']
        seed = request.json['seed']
        docker_tag = request.json['docker_tag']
        pull_request = request.json.get('pull_request', None)

        kv = get_eval_jobs_kv_store()

        job = dict(status=constants.JOB_STATUS_TO_START,
                   eval_spec=dict(problem=problem, eval_id=eval_id,
                                  eval_key=eval_key,
                                  seed=seed, docker_tag=docker_tag,
                                  pull_request=pull_request))

        submitted = kv.compare_and_swap(key=eval_id,
                                        expected_current_value=None,
                                        new_value=job)

        if not submitted:
            ret = make_error('eval_id has already been processed', 403)
        else:
            ret = jsonify({'success': True})

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
