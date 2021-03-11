import logging
from raw.db import  result, result_from_file

def test_logging_exception_result(caplog):
    """Errors should be surfaced and logged,
    but not stop execution
    """

    # trigger an error
    result("SELECT * FROM nonexistent_relation")

    # assert the expected error was surfaced    
    record = [ record for record in caplog.records][0]
    assert 'relation "nonexistent_relation" does not exist' in record.message

    # execution should still be possible
    result("SELECT * from mydatabase")


def test_logging_exception_result_from_file(caplog):
    """Errors should be surfaced and logged,
    but not stop execution
    """

    # trigger an error
    result_from_file("./tests/sql_files/bad.sql")

    # assert the expected error was surfaced    
    record = [ record for record in caplog.records][0]
    assert 'relation "nonexistent_relation" does not exist' in record.message

    # execution should still be possible
    result_from_file("./tests/sql_files/good.sql")
