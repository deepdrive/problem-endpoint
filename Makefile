DEPLOY_ARGS=problem-endpoint-app.yaml --quiet

logs:
	gcloud app logs tail -s deepdrive-problem-endpoint

deploy:
	gcloud app deploy $(DEPLOY_ARGS)

# If you've changed botleague-helpers, in order to pull latest do
fresh_deploy:
	gcloud beta app deploy $(DEPLOY_ARGS) --no-cache
	# Note: Change requirements.txt seems to have the same effect

dispath_deploy:
	gcloud app deploy dispatch.yaml


