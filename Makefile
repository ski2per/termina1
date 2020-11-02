#.PHONY: test e2e-test cover gofmt gofmt-fix header-check clean tar.gz docker-push release docker-push-all flannel-git

# Registry used for publishing images
REGISTRY?=${REGISTRY_PREFIX}terminal
VERSION_FILE=templates/index.html

# Default tag and architecture. Can be overridden
TAG?=$(shell git describe --tags --dirty)
ifeq ($(TAG),)
	TAG=latest
endif

ifeq ($(findstring dirty,$(TAG)), dirty)
	TAG=latest
endif



clean:
	@echo "clean"

## Create a docker image on disk for a specific arch and tag
image:
	@cp $(VERSION_FILE) "$(VERSION_FILE).bak"
	@sed -i "s/VERSION/$(TAG)/" $(VERSION_FILE)
	docker build --no-cache -f Dockerfile -t $(REGISTRY):$(TAG) .
	@mv "$(VERSION_FILE).bak" $(VERSION_FILE)

push: image
	docker push $(REGISTRY):$(TAG)

