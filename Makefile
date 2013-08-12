PACKAGE=curdling
CUSTOM_PIP_INDEX=localshop
TESTS_VERBOSITY=2
# </variables>

EXTRA_TEST_TASKS=


all: test

test: unit functional integration acceptance $(EXTRA_TEST_TASKS)

unit: setup
	@make run_test suite=unit

functional: setup
	@make run_test suite=functional

integration: setup
	@make run_test suite=integration

acceptance: setup
	@make run_test suite=acceptance

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
		pip install --quiet --index-url 'http://yipit:90794720b29311e29e960800200c9a66@localshop.yipit.com/simple/' -r development.txt; \
	fi

run_test:
	@if [ -d tests/$(suite) ]; then \
		if [ "`ls tests/$(suite)/*.py`" = "tests/$(suite)/__init__.py" ] ; then \
			echo "No \033[0;32m$(suite)\033[0m tests..."; \
		else \
			echo "======================================="; \
			echo "* Running \033[0;32m$(suite)\033[0m test suite *"; \
			echo "======================================="; \
			nosetests --stop --with-coverage --cover-package=$(PACKAGE) \
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
		echo "Read more about it here: https://github.com/Yipit/yipit/blob/master/docs/rfc/RFC00007-maintaining-python-packages.md"; \
		exit 1; \
	fi

release: