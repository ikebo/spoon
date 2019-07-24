.PHONY: clean-pyc test

all: test clean-pyc

test:
	python tests/spoon_tests.py

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
