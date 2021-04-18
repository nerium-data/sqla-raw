# sqla-raw

An opinionated, minimalist library for fetching data from a [SQLAlchemy](https://www.sqlalchemy.org/) connection, when you don't need or want an ORM. You know how to write SQL; `sqla-raw` makes it [E-Z](https://media.giphy.com/media/zcCGBRQshGdt6/source.gif) to send that raw SQL to your database and get results, saving a lot of DBAPI boilerplate and providing a simple and consistent interface with a result format that is straightfoward to introspect.

Really not much more than a single method (`raw.db.result()`) that submits raw SQL via a SQLAlchemy [Engine](https://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.Engine) connection. By default, `db.result()` returns all results as a list of dictionaries, keyed by column names. (See __'Usage'__ below for other options)

For convenience, `result_from_file()` and `result_by_name()` allow you to store your SQL in separate local files for submission to the database via `result()` 

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

For longer or more complex queries, you may find it more convenient and maintainable to save your SQL in its own file, rather than include it inline as a string in your Python program. Doing so also allows the queries to be tested and/or reused in your preferred database client tool. `sqla-raw` provides two ways to do this:

`result_from_file()` takes a path (any file-like object should also work) and reads your query from there, rather than taking a SQL string argument directly. Contents of the file are handed off to result() so the rest functions identitically.

`result_by_name()` looks for SQL files in a local directory — `${PWD}/query_files` by default, or you may specify any arbitrary filesystem location by setting `$QUERY_PATH` in the environment. The `query_name` arguement is the [stem](https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.stem) of the desired file.

### SQLAlchemy Engine invocation

By default, Engine instantiation is handled implicitly on first call to `result()`; subsquent calls use a connection from the pool. The default connection string for the Engine is set by `DATABASE_URL` in the environment, and all other Engine settings use SQLAlchemy defaults. This allows you to simply call `result()` and start querying `$DATABASE_URL` immediately with a minimum of fuss. 

In case you require multiple database connections, or more control over Engine parameters, `db.engine()` wraps `sqlalchemy.create_engine()`, so you can set a different connection string or pass additional settings as keyword arguments (see https://docs.sqlalchemy.org/en/14/core/engines.html for options). Once `db.engine()` is explicitly invoked, the engine so instantiated remains as the active connection pool unless changed again.

### Exception handling

Obviously, when interacting with a database, any number of things can go wrong, that may or may not be the fault of your code. Besides obvious syntax errors, inputs to parameters might be the wrong type, the database could be unreachable, credentials incorrect or changed, etc. Early development versions of `sqla-raw` tried to catch any database exceptions and return them formatted like results, on the theory that any calling program wouldn't want to halt execution on such errors. On further reflection, it doesn't seem like a library should be making that decision, and `sqla-raw` as of version 1.x allows any exceptions it may encounter to be raised in the usual way. Any calling code that does not wish to halt on these exceptions may of course simply wrap the call to any `raw.db` method in a try/except block itself. In hindsight, it probably should have been clear this was the right way to do it all along.

## Tests

`pytest` tests are located in [tests/](tests/). Install test prerequisites with `pip install -r tests/requirements.txt`; then they can be run with: `python setup.py test` 

## Alternatives and prior art

These are all fine projects, and if `sqla-raw` appeals to you at all, you owe it to yourself to take a look at them. These and `sqla-raw` are all similar tools with similar SQL-first, non-ORM philosophies. I haven't benchmarked performance for any one of them, but 3 out of 4 use SQLAlchemy under the covers, and I'd be surprised if there are big differences among at least those three. Until some notable difference in performance turns up, the best choice for you is most likely a matter of taste.

- [aiosql](https://github.com/nackjicholson/aiosql) 
  - Supports standard and async I/O
  - Turns SQL files into callable methods
    - Nothing wrong with that, but different from the interface chosen for `sqla-raw` (which takes the SQL or file name as argument to a single `result()` method)
    - Relies on special comments in the SQL
  - Not SQLAlchemy; supports a more limited set of database drivers
  - Doesn't handle database connect instantiation (expects to be given a conn object)
- [PugSQL](https://pugsql.org/)
  - Based on Clojure's HugSQL library
  - Uses SQLAlchemy
  - Similar API to `aiosql`, with commented SQL files used to create methods
    - Also generates modules from folders of SQL files, and can load multiple such modules
- [Records](https://github.com/kennethreitz-archive/records)
  - Another SQLALchemy facade, and a big inspiration for `sqla-raw`
  - Doesn't seem to be actively maintained
  - Formats results as a specialized `Record` class, based on [`tablib`](http://docs.python-tablib.org/en/latest/)
    - Again, nothing wrong with that — `sqla-raw` favors a standard list-of-dicts format for results instead, as lighter weight and easier to introspect
