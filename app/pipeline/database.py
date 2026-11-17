import os

import psycopg


def connect_database():
    dsn = os.getenv("MACROCHEF_DATABASE_URL", "dbname=macrochef")
    return psycopg.connect(dsn)
