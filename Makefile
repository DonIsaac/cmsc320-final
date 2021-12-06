IMG = donisaac/cmsc320-final-tutorial
IMG_REMOTE = donisaac/cmsc320-final-tutorial
CONTAINER = final-tutorial


# ==============================================================================

.PHONY: default

default: up



# =================================== PYTHON ===================================

.PHONY: req-save

# Save pip3 package requirements to requirements.txt
save:
	# Conda output format
	# conda list -e > requirements.txt
	# Pip output format
	pip list --format=freeze > requirements.txt



# =================================== DOCKER ===================================

.PHONY: up down rm bash

up: img.build
	docker run -it -v $(shell pwd)/:/home/jovyan/notebooks -p 8888:8888 --name $(CONTAINER) $(IMG)

down:
	docker stop $(CONTAINER)
	# docker rm $(CONTAINER)
rm: down
	docker rm $(CONTAINER)

bash:
	docker exec -it $(CONTAINER) /bin/bash

img.build: Dockerfile final.ipynb requirements.txt
	docker build --tag $(IMG):latest .
	@touch img.build

img.tag: img.build
	@echo "Tagging image..."
	@docker image tag $(IMG):latest $(IMG_REMOTE):latest
	@docker image tag $(IMG):latest $(IMG_REMOTE):$(shell git rev-parse --short HEAD)
	@docker image push --all-tags $(IMG_REMOTE)
	@echo done
	@touch img.tag



# ==================================== UTIL ====================================

clean:
	@rm -f img.build img.tag