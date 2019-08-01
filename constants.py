import os

GCP_REGION = 'us-west2'
GCP_ZONE = GCP_REGION + '-b'
GCP_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT') or \
              os.environ.get('GCP_PROJECT', None)
# EVAL_QUEUE_ID = 'deepdrive-eval-queue'
# EVAL_TASK_ROUTE = '/deepdrive_eval_task_handler'
