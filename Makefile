
APP=rogu

all: test

lint:
	pylint rogu | tee lint.log

update:
	python3 -m pip install -r requirements.txt --target $(APP)/thirdparty --upgrade
	rm -r $(APP)/thirdparty/*.dist-info

build:
	mkdir -p build
	python3 -m zipapp --output build/$(APP) --python "/usr/bin/env python3 -O" --compress $(APP)
	@echo "\n\tHAVE YOU UPDATED THE VERSION NUMBER?"

test:
	./test all

.PHONY: all lint update build test
