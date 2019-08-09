import sys

from botleague_helpers.db import get_db
from box import Box

import utils
from constants import JOB_STATUS_TO_START, INSTANCE_STATUS_USED
from eval_manager import EvaluationManager
from singleton_loop import SingletonLoop, STATUS, REQUESTED, RUNNING


def test_singleton_loop_local():
    singleton_loop_helper(use_firestore=False)


def test_singleton_loop_firestore():
    singleton_loop_helper(use_firestore=True)


def singleton_loop_helper(use_firestore):
    def loop_fn():
        print('yoyoy')

    name = 'test_loop_' + utils.generate_rand_alphanumeric(32)
    loop1 = SingletonLoop(name, loop_fn, force_firestore_db=use_firestore)
    loop1.release_semaphore()
    assert loop1.semaphore_released()
    assert loop1.obtain_semaphore(timeout=0)
    assert loop1.db.get(STATUS) == RUNNING + loop1.id
    assert not loop1.semaphore_requested()  # no other loops yet
    loop2 = SingletonLoop(name, loop_fn, force_firestore_db=use_firestore)
    assert not loop2.obtain_semaphore(timeout=0)  # loop1 needs to grant first
    assert loop1.semaphore_requested().startswith(REQUESTED)
    assert loop1.semaphore_released()
    assert loop2.granted_semaphore()
    loop1.db.delete_all_test_data()


def test_job_trigger():
    # Mark test job as to start
    test_id = utils.generate_rand_alphanumeric(32)
    test_jobs_collection = 'test_jobs_' + test_id
    test_instances_collection = 'test_instances_' + test_id
    jobs_db = get_db(test_jobs_collection, use_boxes=True,
                     force_firestore_db=True)
    instances_db = get_db(test_instances_collection, use_boxes=True,
                          force_firestore_db=True)

    job_id = 'TEST_JOB_' + utils.generate_rand_alphanumeric(32)

    trigger_test_job(instances_db, job_id, jobs_db)


def trigger_test_job(instances_db, job_id, jobs_db):
    eval_mgr = EvaluationManager(jobs_db=jobs_db, instances_db=instances_db)
    test_job = Box({
        'results_callback': 'https://sim.deepdrive.io/results/domain_randomization',
        'status': JOB_STATUS_TO_START,
        'id': job_id,
        'eval_spec': {
            'docker_tag': 'deepdriveio/problem-worker-test',
            'eval_id': job_id,
            'eval_key': 'fake_eval_key',
            'seed': 1,
            'problem': 'domain_randomization',
            'pull_request': None}})
    jobs_db.set(job_id, test_job)
    new_jobs = eval_mgr.check_for_new_jobs()
    if new_jobs:
        assert new_jobs[0].instance_id
        instance_meta = instances_db.get(new_jobs[0].instance_id)

        # So we have real instance meta, but inserted the job into a
        # test collection that the instance is not watching.
        # So the job will not actually run.
        assert instance_meta.status == INSTANCE_STATUS_USED
    jobs_db.delete_all_test_data()
    instances_db.delete_all_test_data()


def run_all(current_module):
    print('running all tests')
    for attr in dir(current_module):
        if attr.startswith('test_'):
            print('running ' + attr)
            getattr(current_module, attr)()


def main():
    current_module = sys.modules[__name__]
    if len(sys.argv) > 1:
        test_case = sys.argv[1]
        getattr(current_module, test_case)()
    else:
        run_all(current_module)


if __name__ == '__main__':
    main()
