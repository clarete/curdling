SHELL=bash

PACKAGE=curdling

CUSTOM_PIP_INDEX=localshop

TESTS_VERBOSITY=2

EXTRA_TEST_TASKS=

DUMMY_PYPI_PORT=8000


all: test

test: unit functional acceptance $(EXTRA_TEST_TASKS)

unit: setup
	@TZ=EST+5EDT make run_test suite=unit

functional: setup
	@make dummypypi_start
	@TZ=EST+5EDT make run_test suite=functional
	@make dummypypi_stop

acceptance: setup
	@make dummypypi_start
	export CURDIR=`pwd`				&& \
	source `which virtualenvwrapper.sh` 		&& \
	mktmpenv -r requirements.txt >/dev/null		&& \
	cd $$CURDIR					&& \
	cucumber tests					&& \
	deactivate
	@make dummypypi_stop


dummypypi_start:
	@make dummypypi_stop
	@(cd tests/dummypypi && python -m SimpleHTTPServer >/dev/null 2>&1 &) && \
		while :; do `curl http://localhost:$(DUMMY_PYPI_PORT) > /dev/null 2>&1` && break; done

dummypypi_stop:
	-@ps aux | grep SimpleHTTPServer | grep -v grep | awk '{ print $$2 }' | xargs kill -9 2>/dev/null


setup: clean
	@if [ -z $$VIRTUAL_ENV ]; then \
		echo "===================================================="; \
		echo "You're not running this from a virtualenv, wtf dude?"; \
		echo "ಠ_ಠ"; \
		echo "===================================================="; \
		exit 1; \
	fi
	@if [ -z $$SKIP_DEPS ]; then \
		echo "Installing dependencies..."; \
		pip install --quiet -r development.txt; \
	fi

run_test:
	@if [ -d tests/$(suite) ]; then \
		if [ "`ls tests/$(suite)/*.py`" = "tests/$(suite)/__init__.py" ] ; then \
			echo "No \033[0;32m$(suite)\033[0m tests..."; \
		else \
			echo "======================================="; \
			echo "* Running \033[0;32m$(suite)\033[0m test suite *"; \
			echo "======================================="; \
			nosetests --rednose --stop --with-coverage --cover-package=$(PACKAGE) \
				--cover-branches --verbosity=$(TESTS_VERBOSITY) -s tests/$(suite) ; \
		fi \
	fi

clean:
	@echo "Removing garbage..."
	@find . -name '*.pyc' -delete
	@rm -rf .coverage *.egg-info *.log build dist MANIFEST

publish:
	@if [ -e "$$HOME/.pypirc" ]; then \
		echo "Uploading to '$(CUSTOM_PIP_INDEX)'"; \
		python setup.py register -r "$(CUSTOM_PIP_INDEX)"; \
		python setup.py sdist upload -r "$(CUSTOM_PIP_INDEX)"; \
	else \
		echo "You should create a file called \`.pypirc' under your home dir."; \
		echo "That's the right place to configure \`pypi' repos."; \
		exit 1; \
	fi
