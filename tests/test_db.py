import os

import pytest
import sqlalchemy.exc
from raw.db import result, result_from_file

os.environ["DATABASE_URL"] = "sqlite:///"


def test_result(caplog):
    # trigger an error, and verify it is raised
    with pytest.raises(sqlalchemy.exc.OperationalError):
        result("SELECT * FROM nonexistent_relation")

    # execution should still be possible
    r = result("SELECT 'bar' as foo;")
    assert r == [{"foo": "bar"}]


def test_result_from_file(caplog):
    # trigger an error, and verify it is raised
    with pytest.raises(sqlalchemy.exc.OperationalError):
        result_from_file("./tests/sql_files/bad.sql")

    # execution should still be possible
    result_from_file("./tests/sql_files/good.sql")
