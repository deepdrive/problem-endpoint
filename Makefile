DEPLOY_ARGS=problem-endpoint-app.yaml --quiet

logs:
	gcloud app logs tail -s deepdrive-problem-endpoint

deploy:
	gcloud beta app deploy $(DEPLOY_ARGS) --no-cache


