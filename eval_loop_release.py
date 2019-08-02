import signal
import sys
import threading
import time

from botleague_helpers.key_value_store import get_key_value_store
import logging as log

from box import Box

import constants
from common import get_eval_jobs_kv_store, get_semaphore_kv
from eval_loop import STOPPED
from eval_manager import EvaluationManager

log.basicConfig(level=log.INFO)


# TODO: Call this when process ends with something like `python eval_loop.py; python close_eval_loop.py`
def release_semaphore():
    semaphore_kv = get_semaphore_kv()
    ret = semaphore_kv.set('value', STOPPED)
    return ret


if __name__ == '__main__':
    release_semaphore()
