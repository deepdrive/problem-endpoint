from botleague_helpers.key_value_store import get_key_value_store

import constants


def get_eval_jobs_kv_store():
    return get_key_value_store(
        constants.EVAL_JOBS_COLLECTION_NAME,
        use_boxes=True)


def get_semaphore_kv():
    semaphore_kv = get_key_value_store(
        constants.EVAL_LOOP_SEMAPHORE_COLLECTION_NAME,
        use_boxes=True)
    return semaphore_kv
