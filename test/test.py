import util
from singleton_loop import SingletonLoop, STATUS, REQUESTED, RUNNING


def test_singleton_loop_local():
    singleton_loop_helper(use_firestore=False)


def test_singleton_loop_firestore():
    singleton_loop_helper(use_firestore=True)


def singleton_loop_helper(use_firestore):
    def loop_fn():
        print('yoyoy')

    name = 'test_loop_' + util.generate_rand_alphanumeric(32)
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


if __name__ == '__main__':
    test_singleton_loop_local()
    test_singleton_loop_firestore()
