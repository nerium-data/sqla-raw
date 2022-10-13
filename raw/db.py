#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Use SQLAlchemy to fetch a result set from a query
"""
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode

import s3fs
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import create_engine, text

# initialize DB without instantiating engine yet
DB = None


def set_dburl():
    """Get $DATABASE_URL from environment, and append APPLICATION_NAME"""
    appname = os.getenv("APPLICATION_NAME", "script/sqla-raw")
    _dburl = os.getenv("DATABASE_URL")

    if not _dburl:
        raise ValueError("You must provide a database url")

    res = _dburl.split("?")
    baseurl = res[0]

    try:
        qs = res[1]
        qs = parse_qs(qs)
    except IndexError:
        qs = {}

    qs["application_name"] = appname
    qs = urlencode(qs, doseq=True)

    dburl = f"{baseurl}?{qs}"
    return dburl


def engine(dburl="", **kwargs):
    """Instantiate SQLAlchemy database Engine object.
    Run implicitly by `connect()` using environmental settings, or may be invoked
    explicitly

    Explicit invocation can be useful to support multiple database connections from a
    single program, or to override default Engine settings as desired

    Args:
        `dburl`: a database connection in URL format.
                 Optional, defaults to `$DATABASE_URL` in the environment
        `kwargs`: key-value pairs with other Engine settings, see
                  https://docs.sqlalchemy.org/en/14/core/engines.html for details
    """
    if not dburl:
        dburl = set_dburl()

    global DB
    if hasattr(DB, "dispose"):
        DB.dispose()  # close any previous engine

    DB = create_engine(dburl, **kwargs)
    return DB


def connect():
    """Connect to SQLAlchemy Engine instance and return connection"""
    global DB
    if not DB:
        DB = engine()  # instantiate default engine if necessary
    conn = DB.connect()
    return conn


def process_template(obj, **kwargs):
    """Render query text using jinja2 sandbox"""
    # TODO: Prevent variable expansion
    env = SandboxedEnvironment()
    template = env.from_string(obj)
    return template.render(kwargs)


def result(sql, returns="dict", autocommit=False, **kwargs):
    """Submit SQL to the engine connection and return results as list of dicts

    Args:
        `sql`: a string containing valid SQL for submission to the database
        `returns`: {"proxy", "tuples", "dict"}, optional
            indicates desired result set format:
                - proxy: returns Result
                - tuples: returns a list of tuples
                - dict (or other): returns a list of dictionaries
            "dict" is default, and will also be the result of any other value
        `autocommit` optional boolean, whether to add autocommit=True to execution
        `kwargs`: key-value pairs assigning values to any named parameters
                   in the query
    """
    with connect() as conn:
        # Render with jinja if template tags appear in query body
        tag_regex = re.compile("{%.*%}")
        if tag_regex.search(sql):
            sql = process_template(sql, **kwargs)

        # Execute query against SQLA Engine connection
        sql_text = text(sql)
        if autocommit:
            sql_text = sql_text.execution_options(autocommit=True)
        cur = conn.execute(sql_text, **kwargs)

        # Prepare return object:
        # Handle statements without resultsets:
        if not cur.returns_rows:
            if returns == "proxy":
                return cur
            else:
                return []

        # Handle result formatting:
        if returns == "proxy":
            return cur  # Return naked SQLA Result object
        elif returns == "tuples":
            return list(cur)  # Return all rows as list of tuples
        else:
            # Default: return all rows as list of dictionaries
            return [dict(row) for row in cur]


def result_from_file(path, returns="dict", autocommit=False, **kwargs):
    """Read SQL from file at `path` and submit via `result()` method"""
    # If `path` is a S3 url, read it from there
    if path.startswith("s3://"):
        bucket = s3fs.S3FileSystem(anon=False)
        with bucket.open(path, "rt") as f:
            sql = f.read()
    # Otherwise treat `path` as a local file
    else:
        pathobj = Path(path)
        # If path doesn't exist
        if not pathobj.exists():
            raise IOError(f"File '{path}' not found!")

        # If it's a directory
        if pathobj.is_dir():
            raise IOError(f"'{path}' is a directory!")

        # Read the given file into memory and pass to result().
        with open(path) as f:
            sql = f.read()
    rows = result(sql=sql, returns=returns, autocommit=autocommit, **kwargs)
    return rows


def list_queries():
    """Get a list of all the SQL files in the query path"""
    query_path = os.getenv("QUERY_PATH", "query_files")

    # if `query_path` is a S3 url, get list of all SQL files from there
    if query_path.startswith("s3://"):
        bucket = s3fs.S3FileSystem(anon=False)
        queries = list(bucket.glob(f"{query_path}/**.sql"))
        queries = [f"s3://{i}" for i in queries]
    # otherwise poll local filesystem
    else:
        queries = list(Path(query_path).glob("**/*.sql"))
        queries = [str(i) for i in queries]
    return queries


def path_by_name(query_name):
    """Find file matching query_name and return file handle"""
    # flatten directory and grab all the leaf nodes
    queries = list_queries()
    query_file = None
    # use regex to find the stem of the file name, and check for a match with query_name
    # (s3 file handles are just strings and don't support path.stem();
    #  this works for both)
    rg = re.compile("[ \\w-]+?(?=\\.)")
    query_file_match = list(
        filter(lambda i: query_name == str(rg.findall(i)[0]), queries)
    )
    if query_file_match:
        # TODO: Warn if more than one match (because we flatten subdirectories)
        query_file = query_file_match[0]
    return query_file


def result_by_name(query_name, returns="dict", autocommit=False, **kwargs):
    """Find SQL file at `$QUERY_PATH/name` and pass to `result_from_file()`"""
    path = path_by_name(query_name)
    result = result_from_file(
        path=path, returns=returns, autocommit=autocommit, **kwargs
    )
    return result
