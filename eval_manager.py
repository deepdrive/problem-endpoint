from typing import List

import googleapiclient.discovery
from kubernetes import client as k8s
import kubernetes_utils as cluster
import os, requests
from box import Box, BoxList
from botleague_helpers.key_value_store import get_key_value_store, \
    SimpleKeyValueStore

# Our list of supported problems
import constants

SUPPORTED_PROBLEMS = ['domain_randomization']

# TODO:
#   [x] We get a call from BL with the eval_id
#   For problem and bot container
#   Store the job information in Firestore with the instance-id before starting instance (get from instance creation or from DB on startup)
#      Here's how you get the instance id on an instance curl "http://metadata.google.internal/computeMetadata/v1/instance/id" -H "Metadata-Flavor: Google"
#   Start a sim and bot instance in the loop, if none available, create.
#   If this is a CI run, we'll have to build and push the container first.
#   If an instance is already created but stopped, then start it
#   If an instance is already started (check gcloud api with list filter) and available (which can be determined by querying firestore), set Firestore's new job data with instance id
#   Instances will have startup script that checks Firestore for its instance by subscribing to Firestore event
#   All calls in loop should be async, just one sleep at the end.
#   Send results to PROBLEM_CALLBACK from sim and bot which then sets Firestore and forwards the results to BOTLEAGUE_CALLBACK (for sim only).
#   If the container process ends with a non-zero exit status, send an error response back to problem endpoint callback with a `docker run ... || send_failure_response.py`
#   To detect failed instances, slowly query instance state (once per minute) as most the time it will be fine.
#   Stop instances after results sent with idle_timeout.
#   Delete/Kill instances if over threshold of max instances. (Meaure start/create over a week, maybe we can just create)

"""
# The number of queries are limited to a maximum of 10 queries per minute per VM instance.
# Queries do not exceed a burst of 3 queries per second. If this maximum rate is exceeded,
 Compute Engine might arbitrarily remove guest attributes that are in the process of being written.
 This data removal is needed to ensure that other critical system data can be written to the server.
"""

# gcloud compute instances add-metadata INSTANCE \
#   --metadata bread=mayo,cheese=cheddar,lettuce=romaine
# gcloud compute instances add-metadata [INSTANCE_NAME] --metadata enable-guest-attributes=TRUE
#


class EvaluationManager:
    """
    The evaluation endpoint implementation for the Deepdrive Problem Endpoint.

    - `problem` is the string identifier for the problem.
    - `eval_id` is the unique identifier for this evaluation run.
    - `eval_key` is the evaluation key to pass back to the Botleague liaison.
    - `seed` is the seed to use for random number generation.
    - `docker_tag` is the tag for the bot container image.
    - `pull_request` is the relevant pull request details, or None.
    """

    _kv: SimpleKeyValueStore = None

    def __init__(self):
        self.operations_in_progress = []

    @property
    def kv(self) -> SimpleKeyValueStore:
        if self._kv is None:
            self._kv = get_key_value_store(
                constants.EVAL_INSTANCES_COLLECTION_NAME,
                use_boxes=True)
        return self._kv

    def check_for_new_jobs(self):
        job_query = self.kv.collection.where('status', '==',
                                             constants.JOB_STATUS_TO_START)
        for job in job_query.stream():
            job = Box(job.to_dict())
            result = self.trigger_eval(job)
            self.operations_in_progress += result.operations
            # TODO: Deal with async operation futures returned from trigger
            #  Create instance
            #  Start instance
            # TODO: Check for failed / crashed instance once per minute
            # TODO: Stop instances if they have been idle for longer than timeout
            # TODO: Cap total max instances
            # TODO: Cap instances per bot owner, using first part of docker tag
            # TODO: Delete instances over threshold

    def trigger_eval(self, job):
        problem = job.eval_spec.problem

        # Verify that the specified problem is supported
        if problem not in SUPPORTED_PROBLEMS:
            raise RuntimeError('unsupported problem "{}"'.format(problem))

        eval_spec = job.eval_spec

        compute = googleapiclient.discovery.build('compute', 'v1')
        eval_instances = list_instances(compute, constants.INSTANCE_EVAL_LABEL)
        self.add_eval_data(eval_instances)

        stopped_instances = [inst for inst in eval_instances
                             if inst.status.lower() == 'terminated']

        started_instances = [inst for inst in eval_instances
                             if inst.status.lower() == 'running']

        for inst in started_instances:
            if inst.eval_data.status.lower() == 'available':
                self.set_job_to_start(inst, eval_spec)
                # Now the instance should Firebase listener should get
                # an event and start the job.
                break
        else:
            if stopped_instances:
                inst = stopped_instances[0]
                self.set_job_to_start(inst, eval_spec)
                # TODO: Start the instance
            else:
                # TODO: Create a new instance
                # TODO: Return create operation and check it
                pass

        # Post a confirmation message to the Botleague liaison
        # (Temporarily disabled until the Botleague liaison's confirmation endpoint goes live)
        # confirmation = requests.post('https://liaison.botleague.io/confirm', data={'eval_key': eval_key})

        # Configure the Kubernetes client API to connect to our GKE cluster
        # try:
        # 	cluster.Configuration.configure_for_gke(os.environ['GCP_ZONE'], os.environ['GKE_CLUSTER_NAME'])
        # except KeyError as err:
        # 	raise RuntimeError('the environment variable {} is missing'.format(err.args[0]))
        #
        # # Create a namespace for the Kubernetes objects associated with the eval run
        # namespace = 'eval-{}'.format(eval_id.lower())
        # cluster.Resources.create_namespace(namespace)
        #
        # # Copy our evaluation credentials secret into the namespace, since pods cannot access secrets from other namespaces
        # credentials = cluster.Resources.read_secret('default', os.environ['GKE_SECRET_NAME'])
        # cluster.Resources.create_secret(namespace, os.environ['GKE_SECRET_NAME'], credentials)
        #
        # # Create a job for the bot pod
        # cluster.Resources.create_job(namespace, 'bot-job', k8s.V1PodSpec(
        # 	containers = [
        # 		k8s.V1Container(
        # 			name = 'bot',
        # 			image = docker_tag,
        # 			env = [
        # 				k8s.V1EnvVar(
        # 					name = 'DEEPDRIVE_SIM_HOST',
        # 					value = 'sim'
        # 				)
        # 			],
        # 			resources = k8s.V1ResourceRequirements(
        # 				requests = {'nvidia.com/gpu': '1'},
        # 				limits = {'nvidia.com/gpu': '1'}
        # 			)
        # 		)
        # 	],
        # 	restart_policy = 'Never'
        # ))
        #
        # # The network ports that the sim container will listen on
        # simPorts = [
        # 	k8s.V1ContainerPort(
        # 		container_port = 5557,
        # 		protocol = 'TCP'
        # 	)
        # ]
        #
        # # The mount path and volume name for projecting our evaluation credentials into the sim pod
        # credentialsDir = '/home/ue4/credentials'
        # credentialsVolume = 'credentials'
        #
        # # Create a job for the sim pod
        # cluster.Resources.create_job(namespace, 'sim-job', k8s.V1PodSpec(
        # 	containers = [
        # 		k8s.V1Container(
        # 			name = 'sim',
        # 			image = 'gcr.io/silken-impulse-217423/deepdrive:problem_{}'.format(problem),
        # 			ports = simPorts,
        # 			env = [
        # 				k8s.V1EnvVar(
        # 					name = 'BOTLEAGUE_CALLBACK',
        # 					value = 'https://liaison.botleague.io/results'
        # 				),
        # 				k8s.V1EnvVar(
        # 					name = 'BOTLEAGUE_EVAL_KEY',
        # 					value = eval_key
        # 				),
        # 				k8s.V1EnvVar(
        # 					name = 'BOTLEAGUE_SEED',
        # 					value = seed
        # 				),
        # 				k8s.V1EnvVar(
        # 					name = 'BOTLEAUGE_PROBLEM',
        # 					value = problem
        # 				),
        # 				k8s.V1EnvVar(
        # 					name = 'CREDENTIALS_DIR',
        # 					value = credentialsDir
        # 				)
        # 			],
        # 			resources = k8s.V1ResourceRequirements(
        # 				requests = {'nvidia.com/gpu': '1'},
        # 				limits = {'nvidia.com/gpu': '1'}
        # 			),
        # 			volume_mounts = [
        # 				k8s.V1VolumeMount(
        # 					name = credentialsVolume,
        # 					mount_path = credentialsDir,
        # 					read_only = True
        # 				)
        # 			]
        # 		)
        # 	],
        # 	restart_policy = 'Never',
        # 	volumes = [
        # 		k8s.V1Volume(
        # 			name = credentialsVolume,
        # 			secret = k8s.V1SecretVolumeSource(
        # 				secret_name = os.environ['GKE_SECRET_NAME'],
        # 				items = [
        # 					k8s.V1KeyToPath(
        # 						key = 'youtube-client-secret',
        # 						path = '.client_secrets.json'
        # 					),
        # 					k8s.V1KeyToPath(
        # 						key = 'youtube-credentials',
        # 						path = '.youtube-upload-credentials.json'
        # 					)
        # 				]
        # 			)
        # 		)
        # 	]
        # ))
        #
        # # Create a headless service to provide DNS resolution to the sim pod
        # cluster.Resources.create_headless_service(
        # 	namespace,
        # 	'sim',
        # 	{'name': 'sim-job'},
        # 	ports = cluster.SpecFactory.service_ports_from_container_ports(simPorts)
        # )
        #
        # # Create label selectors to match our bot and sim pods
        # botSelector = k8s.V1LabelSelector(match_labels={'name': 'bot-job'})
        # simSelector = k8s.V1LabelSelector(match_labels={'name': 'sim-job'})
        #
        # # Prevent the bot pod from communicating with anything other than the sim pod
        # cluster.Resources.create_network_policy(namespace, 'allow-dns', cluster.SpecFactory.network_policy_dns_only(botSelector))
        # cluster.Resources.create_network_policy(namespace, 'allow-sim', cluster.SpecFactory.network_policy_pods_only(botSelector, simSelector))

        # TODO: GCE
        #   Create the app engine task that starts / creates the instance

        # If we reach this point then everything was submitted to the cluster successfully

    def set_job_to_start(self, inst, job_spec):
        inst.eval_data.status = constants.JOB_STATUS_TO_START
        self.set_job_spec(inst, job_spec)

    def add_eval_data(self, eval_instances: BoxList):
        for inst in eval_instances:
            inst_eval_data = self.kv.get(inst.id)
            inst.eval_data = inst_eval_data

    def set_job_spec(self, inst, job_spec):
        inst.eval_data.job_spec = job_spec
        self.kv.set(inst.id, inst.eval_data)


def list_instances(compute, label) -> BoxList:
    if label:
        query_filter = f'labels.{label}:*'
    else:
        query_filter = None
    ret = compute.instances().list(project=constants.GCP_PROJECT,
                                   zone=constants.GCP_ZONE,
                                   filter=query_filter).execute()
    ret = BoxList(ret)
    return ret


def main():
    compute = googleapiclient.discovery.build('compute', 'v1')
    eval_instances = list_instances(compute, label='deepdrive-eval')
    pass


if __name__ == '__main__':
    main()
