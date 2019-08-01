.PHONY: build push run bash test deploy reboot_vm prepare

TAG=gcr.io/silken-impulse-217423/deepdrive-service
SSH=gcloud compute ssh deepdrive-service

build:
	docker build -t $(TAG) .

push:
	docker push $(TAG)

#test: build
#	docker run -it $(TAG) bin/test.sh

ssh:
	$(SSH)

prepare:
	$(SSH) --command "sudo docker image prune -f"
	$(SSH) --command "sudo docker container prune -f"

reboot_vm:
	$(SSH) --command "echo connection successful"
	$(SSH) --command "sudo reboot" || echo "Success!! Error above is due to reboot. Check your VM logs."

deploy: test push prepare reboot_vm

run:
	docker run -it --net=host $(TAG)

bash:
	docker run -it $(TAG) bash
