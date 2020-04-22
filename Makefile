TOP_PATH = $(shell pwd)
test_mysql:
	@export PYTHONPATH=$(TOP_PATH) && python $(TOP_PATH)/tests/test_mysql/test_mysql.py

test_sqlite:
	@export PYTHONPATH=$(TOP_PATH) && python $(TOP_PATH)/tests/test_sqlite/test_sqlite.py

test: test_mysql test_sqlite

clean:
	rm test.db

flake8:
	flake8 --statistics --max-line-length=120 tests aiomyorm

.PHONY: clean test_sqlite test_mysql test flake8