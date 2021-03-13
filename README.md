# sqla-raw

An opinionated, minimalist library for fetching data from a [SQLAlchemy](https://www.sqlalchemy.org/) connection, when you don't need or want an ORM. You know how to write SQL; `sqla-raw` wants to make it as simple as possible to send that SQL to your database and get results.

Really not much more than a single method (`raw.db.result`) making it E-Z to submit raw SQL via a sqla [Engine](https://docs.sqlalchemy.org/en/13/core/connections.html#sqlalchemy.engine.Engine). Returns results as a list of dictionaries, with each dict keyed by column names. 

As a further convenience, `result_from_file` is almost the same except it will read the query from a given path, rather than taking a SQL string argument directly.

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

Because it's SQLAlchemy, you can safely use named parameters in your SQL string with colon-prepended `:key` format, and assign values in `kwargs`.

```python
>>> db.result('select :foo as bar', foo='baz')
[{'bar': 'baz'}]
```

You can also use Jinja2 templating syntax to interpolate the query, if desired. `db.result()` simply inspects the query for template tags (`"{%.*%}"`) and renders the template to SQL before submitting. (It uses a `SandboxedEnvironment` for some measure of injection safety, but avoid this option with untrusted inputs, for obvious reasons.)


## Tests

`pytest` tests are located in [tests/](tests/). Install test prerequisites with `pip install -r tests/requirements.txt`, then they can be run with: `python setup.py test` 
