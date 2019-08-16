import time
import traceback
from typing import Any

import requests
from box import Box
from flask import Flask, jsonify, request

from problem_constants import constants
from common import get_jobs_db, get_instances_db
from problem_constants.constants import RESULTS_CALLBACK, BOTLEAGUE_LIAISON_HOST
from loguru import logger as log

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
def handle_eval_request(problem):
    start = time.time()
    log.info('Starting eval request')
    try:
        # Unpack our endpoint parameters from the URL arguments
        eval_id = request.json['eval_id']
        eval_key = request.json['eval_key']
        seed = request.json['seed']
        docker_tag = request.json['docker_tag']
        json_box = Box(request.json, default_box=True)
        max_seconds = json_box.problem_def.max_seconds or None

        pull_request = request.json.get('pull_request', None)
    except KeyError as err:
        log.error(traceback.format_exc())
        log.exception('Error getting required params')

        # If any or our required parameters were missing,
        # send a "400 Bad Request" response
        ret = make_error('the parameter {} is required'.format(err.args[0]),
                         400)
    else:
        try:
            ret = submit_job(docker_tag, eval_id, eval_key, problem,
                             pull_request, seed, max_seconds)

        except Exception as err:
            # If anything went wrong inside the endpoint logic,
            # send a "500 Internal Server Error" response
            log.error(traceback.format_exc())
            log.exception('Problem submitting job')
            ret = make_error(err, 500)
    log.info(ret)
    log.info(f'Eval request took {time.time() - start} seconds')
    return ret


def submit_job(docker_tag, eval_id, eval_key, problem, pull_request, seed,
               max_seconds):
    messages = []

    start_job_submit = time.time()
    db = get_jobs_db()

    if not max_seconds:
        messages.append(f'max_seconds not set in problem definition, '
                        f'defaulting to '
                        f'{constants.MAX_EVAL_SECONDS_DEFAULT} seconds')
        max_seconds = constants.MAX_EVAL_SECONDS_DEFAULT

    job = dict(status=constants.JOB_STATUS_CREATED,
               results_callback=RESULTS_CALLBACK,
               eval_spec=dict(
                   problem=problem, eval_id=eval_id, eval_key=eval_key,
                   seed=seed, docker_tag=docker_tag,
                   pull_request=pull_request,
                   max_seconds=max_seconds
               ))

    submitted = db.compare_and_swap(key=eval_id,
                                    expected_current_value=None,
                                    new_value=job)

    if not submitted:
        ret = make_error('eval_id has already been processed', 403)
    else:
        ret = jsonify({'success': True, 'message': ' '.join(messages)})

    log.info(f'Save submitted job took {time.time() - start_job_submit} '
             f'seconds')
    return ret


if __name__ == "__main__":
    # Don't use debug mode in production or if you don't want to
    # reload on change.
    app.run(host="0.0.0.0", port=8000, debug=False)
