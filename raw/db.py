#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Use SQLAlchemy to fetch a result set from a query
"""
import os
import re


from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import create_engine, text


def connect():
    """Create SQLAlchemy Engine instance and return connection"""
    db_url = os.getenv("DATABASE_URL", "sqlite:///")
    db = create_engine(db_url)
    conn = db.connect()
    return conn


def process_template(obj, **kwargs):
    """Render query body using jinja2 sandbox"""
    # TODO: Prevent variable expansion
    env = SandboxedEnvironment()
    template = env.from_string(obj)
    return template.render(kwargs)


def result(sql, **kwargs):
    """Submit SQL to the engine connection and return results as list of dicts

    Usage:
        `sql` - a string containing valid SQL for submission to the database
        `kwargs` - key/values pairs assigning values to any named parameters in the query
    """
    try:
        with connect() as conn:
            # Render with jinja if template tags appear in query body
            tag_regex = re.compile("{%.*%}")
            if tag_regex.search(sql):
                sql = process_template(sql, **kwargs)

            # Execute query against SQLA Engine connection
            cur = conn.execute(text(sql), **kwargs)

            # Fetch result set and format as list of dictionaries
            result = cur.fetchall()
            cols = cur.keys()
            rows = [dict(zip(cols, row)) for row in result]

    except Exception as e:
        # In case of any exception, capture it and format as result set
        rows = [{"error": repr(e)}]

    return rows


def result_from_file(path, **kwargs):
    """Read SQL from file at `path` and submit via `result()` method"""
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
        rows = result(sql=sql, **kwargs)
        return rows


if __name__ == "__main__":
    """Calling module directly runs a tiny test."""
    from tempfile import NamedTemporaryFile

    os.environ["DATABASE_URL"] = "sqlite:///"
    with NamedTemporaryFile(mode="w") as temp:
        temp.write("select 'foo' as bar")
        temp.seek(0)
        file_result = result_from_file(temp.name)
    assert file_result == [{"bar": "foo"}]
    print(file_result)
