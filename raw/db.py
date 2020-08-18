#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Use SQLAlchemy engine to fetch a dataset from a query
"""
import os
from tempfile import NamedTemporaryFile

from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import create_engine, text


def connection():
    db_url = os.getenv("DATABASE_URL", "sqlite:///")
    db = create_engine(db_url)
    conn = db.connect()
    return conn


def process_template(obj, **kwargs):
    """Render query body using jinja2 sandbox
    TODO: Prevent variable expansion
    """
    env = SandboxedEnvironment()
    template = env.from_string(obj)
    return template.render(kwargs)


def result(sql, jinja=None, **kwargs):
    try:
        with connection() as conn:
            if jinja:
                sql = process_template(sql, **kwargs)
            cur = conn.execute(text(sql), **kwargs)
            cols = cur.keys()
            result = cur.fetchall()
            rows = [dict(zip(cols, row)) for row in result]
    except Exception as e:
        rows = [{"error": repr(e)}]
    return rows


def result_from_file(path, jinja=None, **kwargs):
    # If path doesn't exist
    if not os.path.exists(path):
        rows = [{"error": f"File '{path}' not found!"}]
        return rows

    # If it's a directory
    if os.path.isdir(path):
        rows = [{"error": f"'{path}' is a directory!"}]
        return rows

    # Read the given .sql file into memory.
    with open(path) as f:
        sql = f.read()
        rows = result(sql=sql, jinja=jinja, **kwargs)
        return rows


if __name__ == "__main__":
    os.environ["DATABASE_URL"] = "sqlite:///"
    with NamedTemporaryFile(mode="w") as temp:
        temp.write("select 'foo' as bar")
        temp.seek(0)
        file_result = result_from_file(temp.name)
    assert file_result == [{"bar": "foo"}]
    print(file_result)
