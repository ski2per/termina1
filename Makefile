#.PHONY: clean push

# Registry used for publishing images
REGISTRY?=docker.cetcxl.local/terminal

# Default tag and architecture. Can be overridden
TAG?=$(shell git describe --tags --dirty)
ifeq ($(TAG),)
	TAG=latest
endif


clean:
	@echo "clean"

## Create a docker image on disk for a specific arch and tag
image:
	docker build -f Dockerfile -t $(REGISTRY):$(TAG) .

push: image
	docker push $(REGISTRY):$(TAG)

