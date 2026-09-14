POETRY ?= poetry

.PHONY: check test schema quality

check:
	$(POETRY) check --lock
	$(POETRY) run ruff check .
	$(POETRY) run ruff format --check .
	$(POETRY) run python -m unittest discover -s scripts/tests
	$(POETRY) run python manage.py check
	$(POETRY) run python manage.py makemigrations --check --dry-run
	$(POETRY) run python manage.py migrate --check

schema:
	mkdir -p artifacts
	$(POETRY) run python manage.py spectacular --file artifacts/openapi.yaml --validate --fail-on-warn

test:
	$(POETRY) run python manage.py collectstatic --noinput --verbosity 0
	$(POETRY) run coverage erase
	$(POETRY) run coverage run manage.py test --verbosity 1
	$(POETRY) run coverage combine
	$(POETRY) run coverage report
	$(POETRY) run coverage html
	$(POETRY) run coverage xml

quality: check schema test
