from time import sleep

from box import Box
from logs import log

from botleague_helpers.db import get_db
from problem_constants import constants


def get_jobs_db():
    return get_db(constants.JOBS_COLLECTION_NAME)


def get_instances_db():
    return get_db(constants.WORKER_INSTANCES_COLLECTION_NAME)


def get_config_db():
    return get_db(constants.EVAL_CONFIG_COLLECTION_NAME)


def add_botleague_host_watch():
    """To get realtime configuration without polling the db, we setup a
        watch on the config val to update memory of each server
        process on App Engine"""
    db = get_config_db()

    # Ensure BOTLEAGUE_LIAISON_HOST is set correctly on app start
    constants.BOTLEAGUE_LIAISON_HOST = db.get('BOTLEAGUE_LIAISON_HOST')

    log.info(f'Initialized botleague liaison host to '
             f'{constants.BOTLEAGUE_LIAISON_HOST}')

    # Create a callback on_snapshot function to capture changes
    def on_botleague_host_change(col_snapshot, changes, read_time):
        for change in changes:
            db_host_value = Box(change.document.to_dict(), default_box=True)
            if db_host_value and db_host_value.BOTLEAGUE_LIAISON_HOST:
                constants.BOTLEAGUE_LIAISON_HOST = \
                    db_host_value.BOTLEAGUE_LIAISON_HOST
            else:
                # Fallback if it's not set in DB
                constants.BOTLEAGUE_LIAISON_HOST = \
                    constants.BOTLEAGUE_LIAISON_HOST
            log.success(f'Communicating with botleague at  '
                        f'{constants.BOTLEAGUE_LIAISON_HOST}')
            # if change.type.name == 'ADDED':
            #     print(u'New city: {}'.format(change.document.id))
            # elif change.type.name == 'MODIFIED':
            #     print(u'Modified city: {}'.format(change.document.id))
            # elif change.type.name == 'REMOVED':
            #     print(u'Removed city: {}'.format(change.document.id))

    col_query = db.collection.where('BOTLEAGUE_LIAISON_HOST', '>=', '')

    # Watch the collection query
    query_watch = col_query.on_snapshot(on_botleague_host_change)

    print(query_watch)


if __name__ == '__main__':
    add_botleague_host_watch()
    while True:
        sleep(1)
