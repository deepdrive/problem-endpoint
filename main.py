from datetime import datetime

import time
import traceback
import json
from box import Box
from flask import Flask, jsonify, request
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from problem_constants import constants
from problem_constants.constants import DIR_DATE_FORMAT

import common
from common import get_jobs_db, get_config_db
from loguru import logger as log

from constants import ON_GAE
from utils import dbox

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


@app.route('/sim-build', methods=['POST'])
def handle_ci_request():
    # TODO: Verify that Travis initiated the request with some shared secret.
    #  Travis will not reveal secret config vars to external pull requests...
    # TODO: Ping slack alert channel when this is called
    db = common.get_jobs_db()
    commit = request.json['commit']
    job_id = f'{datetime.utcnow().strftime(DIR_DATE_FORMAT)}_{commit}'
    run_local_debug = dbox(request.json).run_local_debug or False
    job = Box(id=job_id,
              commit=commit,
              branch=request.json['branch'],
              build_id=request.json['build_id'],
              status=constants.JOB_STATUS_CREATED,
              job_type=constants.JOB_TYPE_SIM_BUILD,
              created_at=SERVER_TIMESTAMP,
              run_local_debug=run_local_debug)
    db.set(job_id, job)
    log.success(f'Created job {job.to_json(indent=2, default=str)}')
    return jsonify({'success': True})


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
            ret = submit_eval_job(docker_tag, eval_id, eval_key, problem,
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


def submit_eval_job(docker_tag, eval_id, eval_key, problem, pull_request, seed,
                    max_seconds):
    messages = []

    start_job_submit = time.time()
    db = get_jobs_db()

    if not max_seconds:
        messages.append(f'max_seconds not set in problem definition, '
                        f'defaulting to '
                        f'{constants.MAX_EVAL_SECONDS_DEFAULT} seconds')
        max_seconds = constants.MAX_EVAL_SECONDS_DEFAULT

    job_id = f'{datetime.utcnow().strftime(DIR_DATE_FORMAT)}_{eval_id}'
    job = Box(id=job_id,
              status=constants.JOB_STATUS_CREATED,
              job_type=constants.JOB_TYPE_EVAL,
              botleague_liaison_host=constants.BOTLEAGUE_LIAISON_HOST,
              created_at=SERVER_TIMESTAMP,
              eval_spec=dict(
                  problem=problem,
                  eval_id=eval_id,
                  eval_key=eval_key,
                  seed=seed, docker_tag=docker_tag,
                  pull_request=pull_request,
                  max_seconds=max_seconds,
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
