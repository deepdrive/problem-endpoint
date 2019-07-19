from kubernetes import client as k8s
import kubernetes_utils as cluster
import os, requests

# Our list of supported problems
SUPPORTED_PROBLEMS = ['domain_randomization']

def EvaluationEndpoint(problem, eval_id, eval_key, seed, docker_tag, pull_request):
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
	
	# Post a confirmation message to the Botleague liaison
	# (Temporarily disabled until the Botleague liaison's confirmation endpoint goes live)
	#confirmation = requests.post('https://liaison.botleague.io/confirm', data={'eval_key': eval_key})
	
	# Configure the Kubernetes client API to connect to our GKE cluster
	try:
		cluster.Configuration.configure_for_gke(os.environ['GKE_CLUSTER_ZONE'], os.environ['GKE_CLUSTER_NAME'])
	except KeyError as err:
		raise RuntimeError('the environment variable {} is missing'.format(err.args[0]))
	
	# Create a namespace for the Kubernetes objects associated with the eval run
	namespace = 'eval-{}'.format(eval_id)
	cluster.Resources.create_namespace(namespace)
	
	# Copy our evaluation credentials secret into the namespace, since pods cannot access secrets from other namespaces
	credentials = cluster.Resources.read_secret('default', os.environ['GKE_SECRET_NAME'])
	cluster.Resources.create_secret(namespace, os.environ['GKE_SECRET_NAME'], credentials)
	
	# Create a job for the bot pod
	cluster.Resources.create_job(namespace, 'bot-job', k8s.V1PodSpec(
		containers = [
			k8s.V1Container(
				name = 'bot',
				image = docker_tag,
				env = [
					k8s.V1EnvVar(
						name = 'DEEPDRIVE_SIM_HOST',
						value = 'sim'
					)
				],
				resources = k8s.V1ResourceRequirements(
					requests = {'nvidia.com/gpu': '1'},
					limits = {'nvidia.com/gpu': '1'}
				)
			)
		],
		restart_policy = 'Never'
	))
	
	# The network ports that the sim container will listen on
	simPorts = [
		k8s.V1ContainerPort(
			container_port = 5557,
			protocol = 'TCP'
		)
	]
	
	# The mount path and volume name for projecting our evaluation credentials into the sim pod
	credentialsDir = '/home/ue4/credentials'
	credentialsVolume = 'credentials'
	
	# Create a job for the sim pod
	cluster.Resources.create_job(namespace, 'sim-job', k8s.V1PodSpec(
		containers = [
			k8s.V1Container(
				name = 'sim',
				image = 'gcr.io/silken-impulse-217423/deepdrive:problem_{}'.format(problem),
				ports = simPorts,
				env = [
					k8s.V1EnvVar(
						name = 'BOTLEAGUE_CALLBACK',
						value = 'https://liaison.botleague.io/results'
					),
					k8s.V1EnvVar(
						name = 'BOTLEAGUE_EVAL_KEY',
						value = eval_key
					),
					k8s.V1EnvVar(
						name = 'BOTLEAGUE_SEED',
						value = seed
					),
					k8s.V1EnvVar(
						name = 'BOTLEAUGE_PROBLEM',
						value = problem
					),
					k8s.V1EnvVar(
						name = 'CREDENTIALS_DIR',
						value = credentialsDir
					)
				],
				resources = k8s.V1ResourceRequirements(
					requests = {'nvidia.com/gpu': '1'},
					limits = {'nvidia.com/gpu': '1'}
				),
				volume_mounts = [
					k8s.V1VolumeMount(
						name = credentialsVolume,
						mount_path = credentialsDir,
						read_only = True
					)
				]
			)
		],
		restart_policy = 'Never',
		volumes = [
			k8s.V1Volume(
				name = credentialsVolume,
				secret = k8s.V1SecretVolumeSource(
					secret_name = os.environ['GKE_SECRET_NAME'],
					items = [
						k8s.V1KeyToPath(
							key = 'youtube-client-secret',
							path = '.client_secrets.json'
						),
						k8s.V1KeyToPath(
							key = 'youtube-credentials',
							path = '.youtube-upload-credentials.json'
						)
					]
				)
			)
		]
	))
	
	# Create a headless service to provide DNS resolution to the sim pod
	cluster.Resources.create_headless_service(
		namespace,
		'sim',
		{'name': 'sim-job'},
		ports = cluster.SpecFactory.service_ports_from_container_ports(simPorts)
	)
	
	# Create label selectors to match our bot and sim pods
	botSelector = k8s.V1LabelSelector(match_labels={'name': 'bot-job'})
	simSelector = k8s.V1LabelSelector(match_labels={'name': 'sim-job'})
	
	# Prevent the bot pod from communicating with anything other than the sim pod
	cluster.Resources.create_network_policy(namespace, 'allow-dns', cluster.SpecFactory.network_policy_dns_only(botSelector))
	cluster.Resources.create_network_policy(namespace, 'allow-sim', cluster.SpecFactory.network_policy_pods_only(botSelector, simSelector))
	
	# If we reach this point then everything was submitted to the cluster successfully
	return {'success': True}
