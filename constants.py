import os

GCP_REGION = 'us-west1'
GCP_ZONE = GCP_REGION + '-b'
GCP_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT') or \
              os.environ.get('GCP_PROJECT', None)
INSTANCE_EVAL_LABEL = 'deepdrive-eval'
EVAL_INSTANCES_COLLECTION_NAME = 'deepdrive_eval_instances'
EVAL_JOBS_COLLECTION_NAME = 'deepdrive_eval_jobs'

JOB_STATUS_TO_START = 'to_start'


# EVAL_QUEUE_ID = 'deepdrive-eval-queue'
# EVAL_TASK_ROUTE = '/deepdrive_eval_task_handler'
