import signal
import time

import logging as log
import traceback
from typing import Union

from botleague_helpers.key_value_store import get_key_value_store

import constants
import util
from eval_manager import EvaluationManager

log.basicConfig(level=log.INFO)

LOOP_POSTFIX = '-loop-id='
RUNNING = 'running' + LOOP_POSTFIX
GRANTED = 'granted' + LOOP_POSTFIX
REQUESTED = 'requested' + LOOP_POSTFIX
STOPPED = 'stopped'
STATUS = 'status'


class SingletonLoop:
    def __init__(self, loop_id, fn, use_firestore_db=False):
        self.fn = fn
        self.loop_id = loop_id
        self.kv = get_key_value_store(loop_id + '_semaphore', use_boxes=True,
                                      use_firestore_db=use_firestore_db)
        self.kill_now = False
        self.id = util.generate_rand_alphanumeric(10)
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def run(self):
        self.obtain_semaphore()
        while not self.semaphore_released() or self.kill_now:
            self.fn()
            time.sleep(1)
            # TODO: Ping cronitor every minute
        if self.kill_now:
            self.release_semaphore()

    def obtain_semaphore(self, timeout=None):
        start = time.time()
        if self.kv.get(STATUS) == STOPPED:
            self.kv.set(STATUS, RUNNING + self.id)
            return True
        self.request_semaphore()
        while not self.granted_semaphore():
            log.error('Waiting for other eval loop to end')
            if timeout is not None and time.time() - start > timeout:
                return False
            else:
                time.sleep(1)

    def request_semaphore(self):
        self.kv.set(STATUS, REQUESTED + self.id)

    def granted_semaphore(self):
        ret = self.kv.compare_and_swap(
            key=STATUS,
            expected_current_value=GRANTED + self.id,
            new_value=RUNNING + self.id)
        return ret

    def semaphore_released(self):
        req = self.semaphore_requested()
        if req:
            if req == STOPPED:
                log.info('Stop loop requested from db')
            elif req.startswith(REQUESTED):
                self.grant_semaphore(req)
                log.info('End loop requested, granted and stopping')
            else:
                log.info('Stopping for unexpected status %s', req)
            return True
        else:
            return False

    def semaphore_requested(self) -> Union[bool, str]:
        status = self.kv.get(STATUS)
        if status == RUNNING + self.id:
            return False
        else:
            log.info('Semaphore changed to %s, stopping', status)
            if not status.startswith(REQUESTED) and status != STOPPED:
                log.error('Unexpected semaphore status %s', status)
            return status

    def grant_semaphore(self, req):
        self.kv.set(STATUS, req.replace(REQUESTED, GRANTED))
        log.info('Granted semaphore to %s', req)

    def release_semaphore(self):
        self.kv.set(STATUS, STOPPED)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True


def main():
    eval_mgr = EvaluationManager()
    SingletonLoop(loop_id=constants.EVAL_LOOP_ID,
                  fn=eval_mgr.check_for_new_jobs).run()


if __name__ == '__main__':
    main()
