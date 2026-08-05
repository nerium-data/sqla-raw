import os
from pathlib import Path
from unittest import mock

import pytest
import sqlalchemy.exc
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy.engine.result import Result

from raw.db import (
    engine,
    prepare_key,
    read_key,
    result,
    result_from_file,
    result_by_name,
    stream,
    stream_result_by_name,
)

PASSPHRASE = "super-groovy-big-secret"


@pytest.fixture(autouse=True)
def mock_settings_env_vars():
    query_path = Path(__file__).resolve().parent / "sql_files"
    with mock.patch.dict(
        os.environ, {"DATABASE_URL": "sqlite:///", "QUERY_PATH": str(query_path)}
    ):
        # Keep tests hermetic: real keypair settings in a developer's shell must
        # not leak in and change what the code under test does. `patch.dict`
        # restores the whole environment on exit, so popping here is safe.
        for var in ("PRIVATE_KEY", "PRIVATE_KEY_PATH", "PRIVATE_KEY_PASSPHRASE"):
            os.environ.pop(var, None)
        yield


def test_result():
    # trigger an error, and verify it is raised
    with pytest.raises(sqlalchemy.exc.OperationalError):
        result("select * from nonexistent_relation")

    # execute valid SQL and verify results
    r = result("select 'bar' as foo;")
    assert r == [{"foo": "bar"}]


def test_result_from_file():
    # trigger an error, and verify it is raised
    with pytest.raises(sqlalchemy.exc.OperationalError):
        result_from_file("./tests/sql_files/bad.sql")

    # execute SQL from file, verify results in tuple format using Jinja2
    r = result_from_file("./tests/sql_files/good.sql", returns="tuples", more=True)
    assert r == [("bar",), ("baz",)]


def test_result_by_name():
    # trigger an error, and verify it is raised
    with pytest.raises(sqlalchemy.exc.OperationalError):
        result_by_name("bad")
    # execute SQL from file, verify results in tuple format using Jinja2
    r = result_by_name("good", returns="tuples", more=True)
    assert r == [("bar",), ("baz",)]


def test_proxy_result():
    # return sqla proxy Result object, verify type and contents of response
    engine()
    r = result("select 'bar' as foo;", returns="proxy")
    assert isinstance(r, Result)
    row = r.fetchone()
    assert row.foo == "bar"


def test_ddl_result():
    engine()
    result("create table if not exists foo (id int, bar text)", returns="proxy")
    result("insert into foo values (1, 'baz')")
    r = result("select * from foo", returns="tuples")
    assert r == [
        (1, "baz"),
    ]


@mock.patch.dict(os.environ, {"DATABASE_URL": ""})
def test_missing_dburl_raises_exception():
    with pytest.raises(ValueError):
        engine(dburl=None)


def test_stream_result_by_name():
    r = stream_result_by_name("good", more=True)
    assert next(r) == {"foo": "bar"}
    assert next(r) == {"foo": "baz"}


def test_stream():
    s = stream("select 'bar' as foo;", dict)
    assert next(s) == {"foo": "bar"}


def test_stream_return_type():
    s = stream("select 'bar' as foo;", lambda s: f"<{s['foo']}>")
    assert next(s) == "<bar>"


def test_stream_empty():
    s = stream("select null limit 0;")
    with pytest.raises(StopIteration):
        next(s)


def test_stream_error():
    s = stream("select * from nonexistent_relation")
    with pytest.raises(sqlalchemy.exc.OperationalError):
        next(s)


def pem_key(passphrase=None):
    """Generate a PEM-formatted private key for the keypair auth tests"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    if passphrase:
        encryption = serialization.BestAvailableEncryption(passphrase.encode())
    else:
        encryption = serialization.NoEncryption()
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )


@pytest.fixture
def keyfile(tmp_path):
    """Write an encrypted key to disk and return its path"""
    path = tmp_path / "rsa_key.p8"
    path.write_bytes(pem_key(PASSPHRASE))
    return path


def test_read_key_returns_none_when_unset():
    assert read_key() is None


def test_read_key_from_path(keyfile):
    with mock.patch.dict(os.environ, {"PRIVATE_KEY_PATH": str(keyfile)}):
        assert read_key() == keyfile.read_bytes()


def test_read_key_from_literal():
    key = pem_key()
    with mock.patch.dict(os.environ, {"PRIVATE_KEY": key.decode()}):
        assert read_key() == key


def test_read_key_restores_escaped_newlines():
    key = pem_key()
    escaped = key.decode().replace("\n", "\\n")
    with mock.patch.dict(os.environ, {"PRIVATE_KEY": escaped}):
        assert read_key() == key


def test_read_key_path_takes_precedence_over_literal(keyfile):
    env = {
        "PRIVATE_KEY_PATH": str(keyfile),
        "PRIVATE_KEY": pem_key().decode(),
    }
    with mock.patch.dict(os.environ, env):
        assert read_key() == keyfile.read_bytes()


def test_prepare_key_returns_none_when_unset():
    assert prepare_key() is None


@pytest.mark.parametrize("source", ["PRIVATE_KEY_PATH", "PRIVATE_KEY"])
def test_prepare_key_from_either_source(tmp_path, source):
    key = pem_key(PASSPHRASE)
    if source == "PRIVATE_KEY_PATH":
        path = tmp_path / "rsa_key.p8"
        path.write_bytes(key)
        env = {source: str(path)}
    else:
        env = {source: key.decode()}
    env["PRIVATE_KEY_PASSPHRASE"] = PASSPHRASE

    with mock.patch.dict(os.environ, env):
        pkb = prepare_key()

    # DER-encoded PKCS8, decrypted, as the Snowflake driver expects
    assert isinstance(pkb, bytes)
    serialization.load_der_private_key(pkb, password=None)


def test_prepare_key_without_passphrase():
    with mock.patch.dict(os.environ, {"PRIVATE_KEY": pem_key().decode()}):
        pkb = prepare_key()
    serialization.load_der_private_key(pkb, password=None)


def test_prepare_key_wrong_passphrase_raises():
    env = {"PRIVATE_KEY": pem_key(PASSPHRASE).decode(), "PRIVATE_KEY_PASSPHRASE": "nope"}
    with mock.patch.dict(os.environ, env):
        with pytest.raises(ValueError):
            prepare_key()


def test_engine_ignores_key_for_non_snowflake_url():
    """A key in the env must not be passed to a non-Snowflake driver"""
    with mock.patch.dict(os.environ, {"PRIVATE_KEY": pem_key().decode()}):
        with mock.patch("raw.db.create_engine") as create:
            engine(dburl="sqlite:///")
    assert "connect_args" not in create.call_args.kwargs


def test_engine_passes_key_for_snowflake_url():
    with mock.patch.dict(os.environ, {"PRIVATE_KEY": pem_key().decode()}):
        with mock.patch("raw.db.create_engine") as create:
            engine(dburl="snowflake://user@account/db")
    assert "private_key" in create.call_args.kwargs["connect_args"]


def test_engine_without_key_omits_connect_args():
    with mock.patch("raw.db.create_engine") as create:
        engine(dburl="snowflake://user@account/db")
    assert "connect_args" not in create.call_args.kwargs


def test_engine_merges_key_into_caller_connect_args():
    """A caller's driver options must survive alongside the injected key"""
    with mock.patch.dict(os.environ, {"PRIVATE_KEY": pem_key().decode()}):
        with mock.patch("raw.db.create_engine") as create:
            engine(
                dburl="snowflake://user@account/db",
                connect_args={"warehouse": "wh", "role": "analyst"},
            )
    connect_args = create.call_args.kwargs["connect_args"]
    assert connect_args["warehouse"] == "wh"
    assert connect_args["role"] == "analyst"
    assert "private_key" in connect_args


def test_engine_caller_private_key_beats_environment():
    """An explicitly passed key wins, and the environment is left unread"""
    env = {"PRIVATE_KEY": pem_key().decode(), "PRIVATE_KEY_PASSPHRASE": PASSPHRASE}
    with mock.patch.dict(os.environ, env):
        with mock.patch("raw.db.create_engine") as create:
            with mock.patch("raw.db.prepare_key") as prepare:
                engine(
                    dburl="snowflake://user@account/db",
                    connect_args={"private_key": b"caller-supplied"},
                )
    assert create.call_args.kwargs["connect_args"]["private_key"] == b"caller-supplied"
    prepare.assert_not_called()


def test_engine_preserves_connect_args_for_non_snowflake_url():
    with mock.patch("raw.db.create_engine") as create:
        engine(dburl="sqlite:///", connect_args={"timeout": 30})
    assert create.call_args.kwargs["connect_args"] == {"timeout": 30}


def test_engine_tolerates_explicit_none_connect_args():
    with mock.patch("raw.db.create_engine") as create:
        engine(dburl="sqlite:///", connect_args=None)
    assert "connect_args" not in create.call_args.kwargs


def test_engine_passes_through_other_kwargs():
    with mock.patch.dict(os.environ, {"PRIVATE_KEY": pem_key().decode()}):
        with mock.patch("raw.db.create_engine") as create:
            engine(dburl="snowflake://user@account/db", pool_size=5, echo=True)
    assert create.call_args.kwargs["pool_size"] == 5
    assert create.call_args.kwargs["echo"] is True
    assert "private_key" in create.call_args.kwargs["connect_args"]
