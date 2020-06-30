#!/bin/bash

PYTHON=python3.7

all: clean setup

setup:
	@echo "Installing packages.."
	${PYTHON} -m pip install pipenv && \
	pipenv install --dev --pre

clean:
	@echo "Cleaning up.."
	pipenv --rm || true

test:
	@echo "Running tests.."
	pytest -v

lint:
	@echo "Linting code.."
	black src/ tests/
