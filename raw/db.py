#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Use SQLAlchemy to fetch a result set from a query
"""
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import create_engine, text

DEFAULT_BATCH_SIZE = 4096

# initialize DB without instantiating engine yet
DB = None


def set_dburl():
    """Get $DATABASE_URL from environment, and append APPLICATION_NAME if Postgres"""
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

    if baseurl.startswith("postgres"):
        appname = os.getenv("APPLICATION_NAME", "script/sqla-raw")
        qs["application_name"] = appname

    qs = urlencode(qs, doseq=True)
    dburl = f"{baseurl}?{qs}"

    return dburl


def prepare_key():
    keyfile = os.getenv("PRIVATE_KEY_PATH")
    with open(keyfile, "rb") as key:
        p_key = serialization.load_pem_private_key(
            key.read(),
            password=os.getenv("PRIVATE_KEY_PASSPHRASE").encode(),
            backend=default_backend(),
        )

    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return pkb


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
                  https://docs.sqlalchemy.org/en/latest/core/engines.html for details
    """
    if not dburl:
        dburl = set_dburl()

    global DB
    if hasattr(DB, "dispose"):
        DB.dispose()  # close any previous engine

    # Get key for Snowflake connection if provided in env
    if os.getenv("PRIVATE_KEY_PATH") and dburl.startswith("snowflake"):
        pkb = prepare_key()
        DB = create_engine(dburl, connect_args={"private_key": pkb}, **kwargs)
    else:
        DB = create_engine(dburl, **kwargs)
    return DB


def connect():
    """Connect to SQLAlchemy Engine instance and return connection"""
    global DB
    if not DB:
        DB = engine()  # instantiate default engine if necessary
    conn = DB.begin()
    return conn


def process_template(obj, **kwargs):
    """Render query text using jinja2 sandbox"""
    # TODO: Prevent variable expansion
    env = SandboxedEnvironment()
    template = env.from_string(obj)
    return template.render(kwargs)


def prepare_sql_text(sql, autocommit=False, **kwargs):
    tag_regex = re.compile("{%.*%}")
    if tag_regex.search(sql):
        sql = process_template(sql, **kwargs)

    sql_text = text(sql)
    if autocommit:
        sql_text = sql_text.execution_options(autocommit=True)

    return sql_text


def result(sql, returns="dict", autocommit=False, **kwargs):
    """
    Submit SQL to the engine connection and return results as list of dicts

    Args:
        `sql`: a string containing valid SQL for submission to the database
        `returns`: {"proxy", "tuples", "dict"}, optional
            indicates desired result set format:
                - proxy: returns `CursorResult`
                - tuples: returns a list of `Row`s (like named tuples)
                - dict (or other): returns a list of `RowMapping`s (like dictionaries)
            "dict" is default, and will also be the result of any other value
        `autocommit` optional boolean, whether to add autocommit=True to execution
        `kwargs`: key-value pairs assigning values to any named parameters
                  in the query

    """
    with connect() as conn:
        sql_text = prepare_sql_text(sql, autocommit=autocommit, **kwargs)
        cur = conn.execute(sql_text, parameters=kwargs)
        # conn.commit()

        if returns == "proxy":
            # Return naked SQLA Result object
            return cur

        if not cur.returns_rows:
            # Handle statements without results
            return []

        elif returns == "tuples":
            # Return all rows as list of tuple-like SQLA `Row`s
            return list(cur)
        else:
            # Default: return all rows as list of dictionary-like `RowMapping`s
            return cur.mappings().all()


def stream(sql, return_type=dict, batch_size=DEFAULT_BATCH_SIZE, **kwargs):
    """Submit SQL to the engine connection and return results as list of dicts

    Args:
        `sql`: a string containing valid SQL for submission to the database
        `return_type`: Callable that results are mapped by
        `batch_size`: number of rows fetched by the cursor at once
        `kwargs`: key-value pairs assigning values to any named parameters
                  in the query

    Yields:
        cursor results mapped by `return_type`

    """
    with connect() as conn:
        conn = conn.execution_options(stream_results=True, max_row_buffer=batch_size)
        sql_text = prepare_sql_text(sql, **kwargs)
        result = conn.execute(sql_text, parameters=kwargs)
        yield from map(return_type, result.mappings())


def sql_from_file(path):
    """Read SQL from file at `path` and submit via `result()` method"""
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
    return sql


def result_from_file(path, **kwargs):
    """Extracted but maintained for backwards compatibility"""

    return result(sql_from_file(path), **kwargs)


def list_queries():
    """Get a list of all the SQL files in the query path"""
    query_path = os.getenv("QUERY_PATH", "query_files")

    queries = list(Path(query_path).glob("**/*.sql"))
    queries = [str(i) for i in queries]
    return queries


def path_by_name(query_name):
    """Find file matching query_name and return file handle"""
    # flatten directory and grab all the leaf nodes
    queries = list_queries()
    query_file = None
    # Check for match between query_name and file from list
    query_file_match = list(filter(lambda i: query_name == Path(i).stem, queries))
    if query_file_match:
        # TODO: Warn if more than one match (because we flatten subdirectories)
        query_file = query_file_match[0]
    else:
        raise IOError(f"No query matching '{query_name}' found in $QUERY_PATH")
    return query_file


def result_by_name(query_name, **kwargs):
    """Find SQL file at `$QUERY_PATH/name`, execute, and return results"""

    path = path_by_name(query_name)
    sql = sql_from_file(path)
    return result(sql, **kwargs)


def stream_result_by_name(query_name, **kwargs):
    """Find SQL file at `$QUERY_PATH/name` and stream results back"""

    path = path_by_name(query_name)
    sql = sql_from_file(path)
    return stream(sql, **kwargs)
