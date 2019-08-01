from kubernetes import client as k8s
import kubernetes_utils as cluster
import os, requests

# Our list of supported problems
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
#   Instances will have startup script that checks Firestore for its instance id every second with splay
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


def EvaluationEndpoint(problem, eval_id, eval_key, seed, docker_tag,
                       pull_request):
    '''
    The evaluation endpoint implementation for the Deepdrive Problem Endpoint.

    - `problem` is the string identifier for the problem.
    - `eval_id` is the unique identifier for this evaluation run.
    - `eval_key` is the evaluation key to pass back to the Botleague liaison.
    - `seed` is the seed to use for random number generation.
    - `docker_tag` is the tag for the bot container image.
    - `pull_request` is the relevant pull request details, or None.
    '''

    # Verify that the specified problem is supported
    if problem not in SUPPORTED_PROBLEMS:
        raise RuntimeError('unsupported problem "{}"'.format(problem))

    # TODO: Get instances tagged deepdrive-eval

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
    return {'success': True}
