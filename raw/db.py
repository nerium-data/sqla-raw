#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Use SQLAlchemy engine to fetch a dataset from a query
"""
import os

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


if __name__ == "__main__":
    os.environ["DATABASE_URL"] = "sqlite:///"
    sql = "select 'foo' as bar"
    result = result(sql)
    assert result == [{"bar": "foo"}]
    print(result)
