import os
from pathlib import Path

import pytest
import sqlalchemy.exc
from sqlalchemy.engine.result import ResultProxy

from raw.db import engine, result, result_from_file, result_by_name

os.environ["DATABASE_URL"] = "sqlite:///"
query_path = Path(__file__).resolve().parent / "sql_files"
os.environ["QUERY_PATH"] = str(query_path)


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


def test_result_by_name():
    # trigger an error, and verify it is raised
    with pytest.raises(sqlalchemy.exc.OperationalError):
        result_by_name("bad")

    # execute SQL from file, verify results in tuple format using Jinja2
    r = result_by_name("good", returns="tuples", more=True)
    assert r == [("bar",), ("baz",)]


def test_proxy_result():
    engine()
    r = result("select 'bar' as foo;", returns="proxy")
    assert isinstance(r, ResultProxy)
    row = r.fetchone()
    assert row.foo == "bar"


def test_ddl_result():
    engine()
    result("create table if not exists foo (id int, bar text)", returns="proxy")
    result("insert into foo values (1, 'baz')")
    r = result("select * from foo", returns="tuples")
    assert r == [
        (1, "baz"),
    ]
