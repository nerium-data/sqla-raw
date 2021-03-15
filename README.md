# sqla-raw

An opinionated, minimalist library for fetching data from a [SQLAlchemy](https://www.sqlalchemy.org/) connection, when you don't need or want an ORM. You know how to write SQL; `sqla-raw` makes it [E-Z](https://media.giphy.com/media/zcCGBRQshGdt6/source.gif) to send that raw SQL to your database and get results, saving a lot of DBAPI boilerplate and providing a simple and consistent interface with a result format that is straightfoward to introspect.

Really not much more than a single method (`raw.db.result()`) that submits raw SQL via a SQLAlchemy [Engine](https://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.Engine) connection. By default, `db.result()` returns all results as a list of dictionaries, keyed by column names. (See __'Usage'__ below for other options)

For convenience, `result_from_file()` and `result_by_name()` allow you to store your SQL in separate local files for submission to the database via `result()`

Engine instantiation is handled implicitly by the first call to `result()`; any subsequent calls use a connection from the pool. The connection string for the Engine is set by `DATABASE_URL` in the environment. All other Engine settings use SQLAlchemy defaults. (Affording explicit creation and disposal of the Engine and exposing the setting of other parameters might be a useful area for further development, if it can be kept simple.)

## Installation

`pip install sqla-raw[pg]`

## Usage

Configure your database connection string by setting `$DATABASE_URL` in your environment.

```python
>>> from raw import db
>>> x = db.result('select version()');
>>> x
[{'version': 'PostgreSQL 10.10 on x86_64-apple-darwin14.5.0, compiled by Apple LLVM version 7.0.0 (clang-700.1.76), 64-bit'}]
```

Because it's SQLAlchemy, you can safely use [named parameters](https://docs.sqlalchemy.org/en/latest/core/sqlelement.html?highlight=textclause#sqlalchemy.sql.expression.TextClause.bindparams) in your SQL string with colon-prepended `:key` format, and assign values in `kwargs`.

```python
>>> db.result('select :foo as bar', foo='baz')
[{'bar': 'baz'}]
```

### Jinja templating

You can also use [Jinja2](https://palletsprojects.com/p/jinja/) templating syntax to interpolate the query, if desired. `db.result()` inspects the query for template tags (`"{%.*%}"`) and renders the template to SQL before submitting if tags are present. (It uses a `SandboxedEnvironment` for some measure of injection safety, but avoid this option with untrusted inputs, for obvious reasons.)

### Options

Passing argument `returns` to `db.result()` (or `result_from_file()`) overrides the default result formatting: `returns="tuples"` brings back a list of tuples with row values instead of dictionaries, and `returns="proxy"` returns the plain SQLAlchemy [ResultProxy](https://docs.sqlalchemy.org/en/latest/core/connections.html?highlight=resultproxy#sqlalchemy.engine.ResultProxy) object directly, for further handling by the caller. The `"proxy"` option allows access to methods (e.g. `fetchone()` or `fetchmany()` ) that `sqla-raw` default usage hides behind its facade; it can also be good for SQL statements (such as `inserts` without `returning` or DDL) that are not expected to return results — although by default these will return an empty list.

### SQL file handling

For longer or more complex queries, it is generally more convenient and maintainable to save your SQL in its own file, rather than include it inline in your Python program. Doing so also allows the queries to be tested and/or reused in your preferred database client tool. `sqla-raw` provides two ways to do this:

`result_from_file()` takes a path (any file-like object should also work) and reads your query from there, rather than taking a SQL string argument directly. Contents of the file are handed off to result() so the rest functions identitically.

`result_by_name()` looks for SQL files in a local directory — `${PWD}/query_files` by default, or you may specify any arbitrary filesystem location by setting `$QUERY_PATH` in the environment. The `query_name` arguement is the [stem](https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.stem) of the desired file.
## Tests

`pytest` tests are located in [tests/](tests/). Install test prerequisites with `pip install -r tests/requirements.txt`; then they can be run with: `python setup.py test` 
