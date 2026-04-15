.PHONY: package clean

# Get the host user's ID and Group ID so Docker can give files back to us
UID := $(shell id -u)
GID := $(shell id -g)

package: clean
	mkdir -p package
	docker run --rm --platform linux/arm64 -v $(PWD):/var/task public.ecr.aws/sam/build-python3.11:latest /bin/bash -c "pip install -r requirements.txt -t ./package && chown -R $(UID):$(GID) ./package"
	cd package && zip -r ../deployment.zip .
	zip -g deployment.zip lambda_function.py
	zip -r -g deployment.zip src/
	rm -rf package

clean:
	rm -rf package deployment.zip
	
deploy: package
	aws lambda update-function-code \
		--function-name stocet-news-aggregation-service \
		--zip-file fileb://deployment.zip \
		--no-cli-pager