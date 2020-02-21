# -*- coding: utf-8 -*-
"""Use SQLAlchemy engine to fetch a dataset
"""
import os
from sqlalchemy import create_engine


def connection():
    db_url = os.getenv("DATABASE_URL", "sqlite:///")
    db = create_engine(db_url)
    conn = db.connect()
    return conn


def result(sql, **kwargs):
    try:
        db = connection()
        cur = db.execute(sql, **kwargs)
        cols = cur.keys()
        result = cur.fetchall()
        rows = [dict(zip(cols, row)) for row in result]
    except Exception as e:
        rows = [{"error": repr(e)}]
    return rows
