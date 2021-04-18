#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Use SQLAlchemy to fetch a result set from a query
"""
import os
import re
from pathlib import Path

from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import create_engine, text

_DBURL = os.getenv("DATABASE_URL", "sqlite:///")
APPNAME = os.getenv("APPLICATION_NAME", "script/sqla-raw")
DBURL = f"{_DBURL}?application_name={APPNAME}"

# initialize DB without instantiating engine yet
DB = None


def engine(dburl=DBURL, **kwargs):
    """Overrride default engine settings

    Args:
        `dburl`: a database connection in URL format.
                 Optional, defaults to `$DATABASE_URL` in the environment
        `kwargs`: key-value pairs with other Engine settings, see
                  https://docs.sqlalchemy.org/en/14/core/engines.html for details
    """
    global DB
    # close any previous engine
    if hasattr(DB, "dispose"):
        DB.dispose()
    DB = create_engine(dburl, **kwargs)
    return DB


def connect():
    """Connect to SQLAlchemy Engine instance and return connection"""
    # instantiate default engine if necessary
    global DB
    if not DB:
        DB = engine()
    conn = DB.connect()
    return conn


def process_template(obj, **kwargs):
    """Render query text using jinja2 sandbox"""
    # TODO: Prevent variable expansion
    env = SandboxedEnvironment()
    template = env.from_string(obj)
    return template.render(kwargs)


def result(sql, returns="dict", **kwargs):
    """Submit SQL to the engine connection and return results as list of dicts

    Args:
        `sql`: a string containing valid SQL for submission to the database
        `returns`: {"proxy", "tuples", "dict"}, optional
            indicates desired result set format:
                - proxy: returns ResultProxy
                - tuples: returns a list of tuples
                - dict (or other): returns a list of dictionaries
            "dict" is default, and will also be the result of any other value
        `kwargs`: key-value pairs assigning values to any named parameters
                   in the query
    """
    with connect() as conn:
        # Render with jinja if template tags appear in query body
        tag_regex = re.compile("{%.*%}")
        if tag_regex.search(sql):
            sql = process_template(sql, **kwargs)

        # Execute query against SQLA Engine connection
        cur = conn.execute(text(sql), **kwargs)

        # Prepare return object:
        # Handle statements without resultsets:
        if not cur.returns_rows:
            if returns == "proxy":
                return cur
            else:
                return []

        # Handle result formatting:
        if returns == "proxy":
            # Return naked SQLA ResultProxy object
            return cur
        elif returns == "tuples":
            # Return all rows as list of tuples
            return list(cur)
        else:
            # Default: return all rows as list of dictionaries
            return [dict(row) for row in cur]


def result_from_file(path, returns="dict", **kwargs):
    """Read SQL from file at `path` and submit via `result()` method"""
    # If path doesn't exist
    if not os.path.exists(path):
        raise IOError(f"File '{path}' not found!")

    # If it's a directory
    if os.path.isdir(path):
        raise IOError(f"'{path}' is a directory!")

    # Read the given file into memory and pass to result().
    with open(path) as f:
        sql = f.read()
        rows = result(sql=sql, returns=returns, **kwargs)
        return rows


def path_by_name(query_name):
    """Find file matching query_name and return Path object"""
    # flatten directory and grab all the leaf nodes
    flat_queries = list(Path(os.getenv("QUERY_PATH", "query_files")).glob("**/*"))
    query_file = None
    query_file_match = list(filter(lambda i: query_name == i.stem, flat_queries))
    if query_file_match:
        # TODO: Warn if more than one match
        query_file = query_file_match[0]
    return query_file


def result_by_name(query_name, returns="dict", **kwargs):
    """Find SQL file at `$QUERY_PATH/name` and pass to `result_from_file()`"""
    path = path_by_name(query_name)
    result = result_from_file(path=path, returns=returns, **kwargs)
    return result
