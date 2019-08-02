import signal
import time

import logging as log
import traceback
from typing import Union

from botleague_helpers.key_value_store import SimpleKeyValueStore

import util
from common import  get_semaphore_kv
from eval_manager import EvaluationManager

log.basicConfig(level=log.INFO)

LOOP_POSTFIX = '-loop-id='
RUNNING = 'running' + LOOP_POSTFIX
GRANTED = 'granted' + LOOP_POSTFIX
REQUESTED = 'requested' + LOOP_POSTFIX
STOPPED = 'stopped'
STATUS = 'status'


class SingletonLoop:
    def __init__(self, fn, name):
        self.fn = fn
        self.name = name
        self.kill_now = False
        self.kv = get_semaphore_kv()
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

    def obtain_semaphore(self):
        if self.kv.get(STATUS) == STOPPED:
            return
        self.request_semaphore()
        while not self.obtained_semaphore():
            log.error('Waiting for other eval loop to end')
            time.sleep(1)

    def request_semaphore(self):
        self.kv.set(STATUS, REQUESTED + self.id)

    def obtained_semaphore(self):
        ret = self.kv.compare_and_swap(
            key=STATUS,
            expected_current_value=GRANTED + self.id,
            new_value=RUNNING + self.id)
        return ret

    def semaphore_released(self):
        req = self.semaphore_requested()
        if req:
            try:
                self.grant_semaphore(req)
            except Exception:
                log.error(traceback.format_exc())
                log.error('Error granting semaphore, stopping')
            else:
                log.info('End loop requested, stopping')
            return True
        else:
            return False

    def semaphore_requested(self) -> Union[bool, str]:
        status = self.kv.get(STATUS)
        if status == RUNNING + self.id:
            return False
        else:
            log.info('Semaphore changed to %s, stopping', status)
            if not status.startswith(REQUESTED):
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
    SingletonLoop(fn=eval_mgr.check_for_new_jobs, name='eval_loop').run()


if __name__ == '__main__':
    main()
