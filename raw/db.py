#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Use SQLAlchemy to fetch a result set from a query
"""
import os
import re


from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import create_engine, text

# For pool efficiency, we should only create the Engine once
DB = create_engine(os.getenv("DATABASE_URL", "sqlite:///"))


def connect():
    """Create SQLAlchemy Engine instance and return connection"""
    conn = DB.connect()
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
        `kwargs` - key/value pairs assigning values to any named parameters
                   in the query
    """
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
    return rows


def result_from_file(path, **kwargs):
    """Read SQL from file at `path` and submit via `result()` method"""
    # If path doesn't exist
    if not os.path.exists(path):
        raise IOError(f"File '{path}' not found!")

    # If it's a directory
    if os.path.isdir(path):
        raise IOError(f"'{path}' is a directory!")

    # Read the given .sql file into memory and pass to result().
    with open(path) as f:
        sql = f.read()
        rows = result(sql=sql, **kwargs)
        return rows
