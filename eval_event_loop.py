import signal
import sys
import threading
import time

from botleague_helpers.key_value_store import get_key_value_store
import logging as log

from box import Box

import constants
from common import get_eval_jobs_kv_store, get_semaphore_kv
from eval_manager import EvaluationManager

log.basicConfig(level=log.INFO)


def eval_loop():
    ensure_alone()
    kv = get_eval_jobs_kv_store()
    eval_mgr = EvaluationManager()
    operations_in_progress = []

    while True:
        if alone():
            eval_mgr.check_for_new_jobs()
        else:
            log.error('Not checking jobs. '
                      'Deferring to most recently started eval loop.')
        time.sleep(1)


def alone():
    semaphore_kv = get_key_value_store(
        constants.EVAL_LOOP_SEMAPHORE_COLLECTION_NAME,
        use_boxes=True)
    ret = semaphore_kv.compare_and_swap('status', 'stopped', 'running')
    return ret


def ensure_alone():
    semaphore_kv = get_semaphore_kv()
    ret = semaphore_kv.set('status', 'stopped')
    return ret


def main():
    pass
    # Add a job to the db and check that we can get notified about it
    # kv = get_eval_jobs_kv_store()
    # kv.set('some-eval-id-LKJHLKJHLJKHLKJHSDF', {
    #     "status": "to_start",
    #     "args": {
    #         "eval_id": "some-eval-id-LKJHLKJHLJKHLKJHSDF",
    #         "problem": "domain_randomization",
    #     }
    # })
    # pass


if __name__ == '__main__':
    eval_loop()
