Deepdrive Problem Endpoint
==========================

The Google App Engine (GAE) service in this repository is the [Botleague Problem Endpoint](https://github.com/botleague/botleague#problem-endpoints) for all problems that use the Deepdrive simulator.

This app works in conjunction with the [problem-coordinator](https://github.com/deepdrive/problem-coordinator)
and [problem-worker](https://github.com/deepdrive/problem-worker).

Communication between these apps happens via Firestore.

This endpoint's responsibility is to implement the Botleague problem API for
Deepdrive. Jobs are managed by the problem-coordinator on GCE which is an
event loop that starts instances and assigns eval jobs to them. 

The problem-worker processes run on the large instances alongside the sim or bot container
and deal with those containers' local lifecycles.


## Reusability

The endpoint, coordinator, and worker have all been designed so that you could
easily re-use them for another problem on GCP, say vehicle detection, by changing
constants.py and instance config JSON files.

## Setup

```
pip install -r requirements.txt
```


## Deploy, logs, etc..

See Makefile


## Legal

Copyright &copy; 2019, [Deepdrive](https://deepdrive.io/). Licensed under the MIT License, see the file [LICENSE](./LICENSE) for details.
