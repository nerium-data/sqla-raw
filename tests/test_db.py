import os

import pytest
import sqlalchemy.exc
from sqlalchemy.engine.result import ResultProxy

from raw.db import result, result_from_file

os.environ["DATABASE_URL"] = "sqlite:///"


def test_result():
    # trigger an error, and verify it is raised
    with pytest.raises(sqlalchemy.exc.OperationalError):
        result("select * from nonexistent_relation")

    # execute valid SQL and verify results
    r = result("select 'bar' as foo;")
    assert r == [{"foo": "bar"}]


def test_result_from_file():
    # trigger an error, and verify it is raised
    with pytest.raises(sqlalchemy.exc.OperationalError):
        result_from_file("./tests/sql_files/bad.sql")

    # execute SQL from file, verify results in tuple format using Jinja2
    r = result_from_file("./tests/sql_files/good.sql", returns="tuples", more=True)
    assert r == [("bar",), ("baz",)]


def test_proxy_result():
    r = result("select 'bar' as foo;", returns="proxy")
    assert isinstance(r, ResultProxy)
    row = r.fetchone()
    assert row.foo == "bar"


def test_ddl_result():
    result("create table if not exists foo (id int, bar text)", returns="proxy")
    result("insert into foo values (1, 'baz')")
    r = result("select * from foo", returns="tuples")
    assert r == [
        (1, "baz"),
    ]
