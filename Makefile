
APP=rogu

lint:
	pylint rogu | tee lint.log

update-deps:
	python3 -m pip install -r requirements.txt --target $(APP)/thirdparty --upgrade
	rm -r $(APP)/thirdparty/*.dist-info

.PHONY: lint update-deps
