import time
import traceback
from typing import Any

import requests
from box import Box
from flask import Flask, jsonify, request

import constants
from common import get_jobs_db, get_instances_db
from constants import RESULTS_CALLBACK
from logs import log

app = Flask(__name__)


# Creates a JSON error response with the specified HTTP status code
def make_error(err, code=400):
    response = jsonify({'error': str(err)})
    response.status_code = code
    return response


@app.route("/")
def index():
    return 'Deepdrive sim service that serves as a Botleague problem ' \
           'endpoint and CI service. ' \
           'Source https://github.com/deepdrive/deepdrive-sim-service'


@app.route('/eval/<problem>', methods=['POST'])
def handle_eval(problem):
    try:
        # Unpack our endpoint parameters from the URL arguments
        eval_id = request.json['eval_id']
        eval_key = request.json['eval_key']
        seed = request.json['seed']
        docker_tag = request.json['docker_tag']
        pull_request = request.json.get('pull_request', None)
    except KeyError as err:
        print(traceback.format_exc())

        # If any or our required parameters were missing,
        # send a "400 Bad Request" response
        ret = make_error('the parameter {} is required'.format(err.args[0]),
                         400)
    else:
        try:
            ret = submit_job(docker_tag, eval_id, eval_key, problem,
                             pull_request, seed)

        except Exception as err:
            # If anything went wrong inside the endpoint logic,
            # send a "500 Internal Server Error" response
            print(traceback.format_exc())
            ret = make_error(err, 500)
    print(ret)
    return ret


def submit_job(docker_tag, eval_id, eval_key, problem, pull_request, seed):
    # TODO: Send confirm request
    confirmation = requests.post('https://liaison.botleague.io/confirm',
                                 data={'eval_key': eval_key})
    if not confirmation.ok:
        ret = make_error('Could not confirm eval with Botleague', 401)
    else:
        db = get_jobs_db()

        job = dict(status=constants.JOB_STATUS_TO_START,
                   eval_spec=dict(
                       problem=problem, eval_id=eval_id, eval_key=eval_key,
                       seed=seed, docker_tag=docker_tag,
                       pull_request=pull_request,
                       results_callback=RESULTS_CALLBACK, ))

        submitted = db.compare_and_swap(key=eval_id,
                                        expected_current_value=None,
                                        new_value=job)

        if not submitted:
            ret = make_error('eval_id has already been processed', 403)
        else:
            ret = jsonify({'success': True})
    return ret


@app.route('/results', methods=['POST'])
def handle_results() -> Any:
    req = Box(request.json)

    log.info(f'Processing results for job \n{req.to_json(indent=2)}')

    instance_id = req.instance_id
    db = get_instances_db()
    instance = db.get(instance_id)
    instance.status = constants.INSTANCE_STATUS_AVAILABLE
    instance.time_last_available = time.time()
    db.set(instance_id, instance)
    log.success(f'Made instance {instance_id} available')

    results_resp = requests.post('https://liaison.botleague.io/results',
                                 data={'eval_key': req.eval_spec.eval_key,
                                       'results': req.results})
    if not results_resp.ok:
        log.error(f'Error posting results back to botleague: {results_resp}')
        ret = make_error(str(results_resp), 500)
    else:
        json_resp = results_resp.json()
        log.success(json_resp)
        ret = json_resp
    return ret


if __name__ == "__main__":
    # Don't use debug mode in production.
    # See Dockerfile for how to run in prod.
    app.run(host="0.0.0.0", port=8000, debug=False)
