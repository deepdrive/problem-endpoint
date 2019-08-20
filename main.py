import time
import traceback
from typing import Any
import json
import requests
from botleague_helpers.db import get_db
from box import Box
from flask import Flask, jsonify, request

from problem_constants import constants

import common
from common import get_jobs_db, get_instances_db, get_config_db
from loguru import logger as log

from constants import ON_GAE

app = Flask(__name__)


# Creates a JSON error response with the specified HTTP status code
def make_error(err, code=400):
    response = jsonify({'error': str(err)})
    response.status_code = code
    return response


@app.route("/")
def index():
    return 'Deepdrive sim service that serves as a Botleague problem ' \
           'endpoint and CI service.<br>' \
           'Source https://github.com/deepdrive/deepdrive-sim-service <br>' \
           f'Botleague host: {constants.BOTLEAGUE_LIAISON_HOST}'


@app.route('/eval/<problem>', methods=['POST'])
def handle_eval_request(problem):
    start = time.time()
    log.info(f'Starting eval request {json.dumps(request.json, indent=2)}')

    db = get_config_db()
    if ON_GAE and db.get('DISABLE_EVAL') is True:
        return make_error('Evals are disabled', 423)

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

    job = Box(status=constants.JOB_STATUS_CREATED,
              botleague_liaison_host=constants.BOTLEAGUE_LIAISON_HOST,
              eval_spec=dict(
                  problem=problem, eval_id=eval_id, eval_key=eval_key,
                  seed=seed, docker_tag=docker_tag,
                  pull_request=pull_request,
                  max_seconds=max_seconds
              ))

    log.info(f'Submitting job {eval_id}: {job.to_json(indent=2)}')

    submitted = db.compare_and_swap(key=eval_id,
                                    expected_current_value=None,
                                    new_value=job.to_dict())

    if not submitted:
        ret = make_error(f'eval_id {eval_id} has already been processed', 403)
    else:
        for msg in messages:
            log.info(msg)
        ret = jsonify({'success': True, 'message': ' '.join(messages)})

    log.info(f'Save submitted job took {time.time() - start_job_submit} '
             f'seconds')
    return ret


common.add_botleague_host_watch()

if __name__ == "__main__":
    # Don't use debug mode in production or if you don't want to
    # reload on change.
    app.run(host="0.0.0.0", port=8000, debug=False)
