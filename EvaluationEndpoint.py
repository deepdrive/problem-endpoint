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
	# (Temporarily commented out until the Botleague liaison goes live)
	#requests.post('https://liaison.botleague.io/confirm', date={'eval_key': eval_key})
	
	# Configure the Kubernetes client API to connect to our GKE cluster
	try:
		cluster.Configuration.configure_for_gke(os.environ['GKE_CLUSTER_ZONE'], os.environ['GKE_CLUSTER_NAME'])
	except KeyError as err:
		raise RuntimeError('the environment variable {} is missing'.format(err.args[0]))
	
	# Create a namespace for the Kubernetes objects associated with the eval run
	namespace = 'eval-{}'.format(eval_id)
	cluster.Resources.create_namespace(namespace)
	
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
				]
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
	
	# Create a job for the sim pod
	cluster.Resources.create_job(namespace, 'sim-job', k8s.V1PodSpec(
		containers = [
			k8s.V1Container(
				name = 'sim',
				image = 'deepdriveio/deepdrive:{}_problem'.format(problem),
				ports = simPorts,
				env = [
					k8s.V1EnvVar(
						# NOTE: this specifies the eval key as a GET parameter, but the docs list it as part of a POST body?
						name = 'BOTLEAGUE_CALLBACK',
						value = 'https://liaison.botleague.io/results?eval_key={}'.format(eval_key)
					),
					k8s.V1EnvVar(
						name = 'BOTLEAGUE_SEED',
						value = seed
					),
					k8s.V1EnvVar(
						name = 'BOTLEAUGE_PROBLEM',
						value = problem
					)
				]
			)
		],
		restart_policy = 'Never'
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
