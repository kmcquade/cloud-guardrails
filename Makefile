SHELL:=/bin/bash

PROJECT := azure-guardrails
PROJECT_UNDERSCORE := azure_guardrails

.PHONY: update-submodule
update-submodule:
	git submodule init
	git submodule update

.PHONY: setup-env
setup-env: update-submodule
	python3 -m venv ./venv && source venv/bin/activate
	python3 -m pip install -r requirements.txt

.PHONY: setup-dev
setup-dev: setup-env
	python3 -m pip install -r requirements-dev.txt

.PHONY: build-docs
build-docs: setup-dev
	mkdocs build

.PHONY: serve-docs
serve-docs: setup-dev
	mkdocs serve --dev-addr "127.0.0.1:8001"

.PHONY: build
build: setup-env clean
	python3 -m pip install --upgrade setuptools wheel
	python3 -m setup -q sdist bdist_wheel

.PHONY: install
install: build
	python3 -m pip install -q ./dist/${PROJECT}*.tar.gz
	${PROJECT} --help

.PHONY: uninstall
uninstall:
	python3 -m pip uninstall ${PROJECT} -y
	python3 -m pip uninstall -r requirements.txt -y
	python3 -m pip uninstall -r requirements-dev.txt -y
	python3 -m pip freeze | xargs python3 -m pip uninstall -y

.PHONY: clean
clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '*.egg-link' -delete
	find . -name '*.pyc' -exec rm --force {} +
	find . -name '*.pyo' -exec rm --force {} +

.PHONY: test
test: setup-dev
	python3 -m coverage run -m pytest -v

.PHONY: security-test
security-test: setup-dev
	bandit -r ./${PROJECT_UNDERSCORE}/

.PHONY: fmt
fmt: setup-dev
	black ${PROJECT_UNDERSCORE}/

.PHONY: lint
lint: setup-dev
	pylint ${PROJECT_UNDERSCORE}/

.PHONY: publish
publish: build
	python3 -m pip install --upgrade twine
	python3 -m twine upload dist/*
	python3 -m pip install ${PROJECT}

.PHONY: count-loc
count-loc:
	echo "If you don't have tokei installed, you can install it with 'brew install tokei'"
	echo "Website: https://github.com/XAMPPRocky/tokei#installation'"
	tokei ./* --exclude --exclude '**/*.html' --exclude '**/*.json'



