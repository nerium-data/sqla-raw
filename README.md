# sqla-raw

I've copy-pasted this enough times that it seemed worth packaging. Really not much more than a single method (`raw.db.result`) making it e-z to submit raw SQL to a database using a SQLAlchemy engine connection. Returns results as a list of dictionaries, with each dict keyed by column names. `result_from_file` is almost the same except it takes a path to read the query from.

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

You can also use Jinja2 templating syntax to interpolate the query, if desired. (It uses a `SandboxedEnvironment`, but avoid this option with untrusted inputs, for obvious reasons.)


## Tests

pytest tests are located in [tests/](tests/)
They are run using [`docker-compose`](https://docs.docker.com/compose/install/) so as to be able to test the package against a mock database.

```bash
docker-compose down && docker-compose build && docker-compose up
```

When tests finish, press `Ctrl+C`
