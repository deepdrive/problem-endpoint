import sys
import time
import logging as log

import requests
import docker

from common import get_eval_jobs_kv_store
from constants import JOB_STATUS_TO_START

log.basicConfig(level=log.INFO)

METADATA_URL = 'http://metadata.google.internal/computeMetadata/v1/instance'


def main():
    instance_id = requests.get(f'{METADATA_URL}/id',
                               headers={'Metadata-Flavor': 'Google'})
    dckr = docker.from_env()
    while True:
        jobs_kv = get_eval_jobs_kv_store()
        job_query = jobs_kv.collection.where('instance_id', '==', instance_id)
        jobs = list(job_query)
        if len(jobs) > 1:
            raise RuntimeError('Got more than one job for instance')
        elif jobs:
            print('No job for instance in db')
        else:
            job = jobs[0]
            if job.status == JOB_STATUS_TO_START:
                docker_tag = job.eval_spec.docker_tag
                container_env = dict(
                    RESULTS_CALLBACK=job.results_callback,
                    BOTLEAGUE_EVAL_KEY=job.eval_key,
                    BOTLEAGUE_SEED=job.seed,
                    BOTLEAUGE_PROBLEM=job.problem,
                )
                container = pull_and_run(dckr, docker_tag, env=container_env)
                exit_code = container.attrs['State']['ExitCode']
                # TODO: Upload the logs
                if exit_code == 0:
                    image = container.attrs['Image'][len('sha256:'):]
                    # dckr.containers.run(image, 'cat results.json')
                    # Use container env['LATEST_BOTLEAGUE_RESULTS'] to get filepath
                    pass
                else:
                    pass
                # TODO: Send error to RESULTS_CALLBACK
                # TODO: Send exit code, logs link

                    pass
        # TODO: Clean up containers and images with LRU and depending on
        #  disk space
        time.sleep(1)


def pull_and_run(docker_client, docker_tag, cmd=None, env=None):
    log.info('pulling docker image %s...', docker_tag)
    log.info(docker_client.images.pull(docker_tag))
    container = docker_client.containers.run(docker_tag, command=cmd,
                                             detach=True, stdout=sys.stdout,
                                             stderr=sys.stderr)
    while container.status in ['created', 'running']:
        container = docker_client.containers.get(container.short_id)
        time.sleep(0.1)

    return container


def play():
    dckr = docker.from_env()
    container = pull_and_run(dckr,
                             'python:3.7',
                             cmd='cat /etc/host.conf')
    container2 = dckr.containers.get(container.short_id)
    log.info(container2.run('cat /etc/host.conf').decode())
    log.info(container.status)


if __name__ == '__main__':
    play()
    # main()

