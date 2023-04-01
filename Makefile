
APP=rogu

lint:
	pylint rogu | tee lint.log

update:
	python3 -m pip install -r requirements.txt --target $(APP)/thirdparty --upgrade
	rm -r $(APP)/thirdparty/*.dist-info

build:
	python3 -m zipapp --output out/$(APP) --python "/usr/bin/env python3 -OO" --compress $(APP)
