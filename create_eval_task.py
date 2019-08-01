# import constants
#
# import argparse
# import datetime
#
# from google.cloud import tasks_v2
# from google.protobuf import timestamp_pb2
#
#
# def create_task(project, queue, location, payload=None, in_seconds=None):
#     """Create a task for a given queue with an arbitrary payload."""
#
#     # Create a client.
#     client = tasks_v2.CloudTasksClient()
#
#     # Construct the fully qualified queue name.
#     parent = client.queue_path(project, location, queue)
#
#     # Construct the request body.
#     task = {
#             'app_engine_http_request': {  # Specify the type of request.
#                 'http_method': 'POST',
#                 'relative_uri': constants.EVAL_TASK_ROUTE
#             }
#     }
#     if payload is not None:
#         # The API expects a payload of type bytes.
#         converted_payload = payload.encode()
#
#         # Add the payload to the request.
#         task['app_engine_http_request']['body'] = converted_payload
#
#     if in_seconds is not None:
#         # Convert "seconds from now" into an rfc3339 datetime string.
#         d = datetime.datetime.utcnow() + datetime.timedelta(seconds=in_seconds)
#
#         # Create Timestamp protobuf.
#         timestamp = timestamp_pb2.Timestamp()
#         timestamp.FromDatetime(d)
#
#         # Add the timestamp to the tasks.
#         task['schedule_time'] = timestamp
#
#     # Use the client to build and send the task.
#     response = client.create_task(parent, task)
#
#     print('Created task {}'.format(response.name))
#     return response
#
#
# if __name__ == '__main__':
#
#
#     # parser = argparse.ArgumentParser(
#     #     description=create_task.__doc__,
#     #     formatter_class=argparse.RawDescriptionHelpFormatter)
#     #
#     # parser.add_argument(
#     #     '--project',
#     #     help='Project of the queue to add the task to.',
#     #     required=True,
#     # )
#     #
#     # parser.add_argument(
#     #     '--queue',
#     #     help='ID (short name) of the queue to add the task to.',
#     #     required=True,
#     # )
#     #
#     # parser.add_argument(
#     #     '--location',
#     #     help='Location of the queue to add the task to.',
#     #     required=True,
#     # )
#     #
#     # parser.add_argument(
#     #     '--payload',
#     #     help='Optional payload to attach to the push queue.'
#     # )
#     #
#     # parser.add_argument(
#     #     '--in_seconds', type=int,
#     #     help='The number of seconds from now to schedule task attempt.'
#     # )
#     #
#     # args = parser.parse_args()
#
#     create_task(
#         constants.GCP_PROJECT, constants.EVAL_QUEUE_ID, constants.GCP_REGION,
#         payload='hello', in_seconds=None)
