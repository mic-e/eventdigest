import signal
import tempfile
import os
import re
import collections
import sqlite3


class TaskFailureError(Exception):
    pass


def run_task(f, timeout=30, capture_output=True, *args, **kwargs):
    oc = OutputCapture() if capture_output else DummyContextManager(output="")
    try:
        with oc:
            with Timeout(timeout) if timeout else DummyContextManager():
                result = f(*args, **kwargs)
    except Exception as e:
        raise TaskFailureError(oc.output) from e

    return result, oc.output


class DummyContextManager:
    """
    for use with a 'with' statement

    >>> with DummyContextManager():
    >>>     pass

    equivalent to nop
    """
    def __init__(self, **kw):
        vars(self).update(kw)

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass


class OutputCapture:
    """
    for use with a 'with' statement

    >>> oc = OutputCapture()
    >>> with oc:
    >>>     print("test")
    >>> oc.output == "test\n"
    """
    def __enter__(self):
        self.f = tempfile.TemporaryFile()

        self.oldstdout = os.dup(1)
        self.oldstderr = os.dup(2)

        os.dup2(self.f.fileno(), 1)
        os.dup2(self.f.fileno(), 2)

    def __exit__(self, type, value, traceback):
        os.dup2(self.oldstdout, 1)
        os.dup2(self.oldstderr, 2)

        os.close(self.oldstdout)
        os.close(self.oldstderr)

        self.f.seek(0)
        self.output = self.f.read().decode('utf-8', errors='replace')
        self.f.close()


class Timeout:
    """
    for use with a 'with' statement

    >>> try:
    >>>     with Timeout(seconds=30):
    >>>         f()
    >>> except TimeoutError as e:
    >>>     print("call to f timed out: %s" % e.args)

    warning: don't mix with threads!
    """

    def __init__(self, timeout=30, error_message='Timeout'):
        self.timeout = timeout
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.timeout)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


class AbstractSQLContainer:
    _allowed_coltypes = {"UNIQUE", }

    def __init__(self, database_filename, table_name, *cols):
        # sanitize inputs that will be passed as SQL commands
        self._sanitize_string(table_name, "table name")
        for col in cols:
            col = col.split(' ')
            self._sanitize_string(col[0], "column name")
            for coltype in col[1:]:
                if coltype not in self._allowed_coltypes:
                    raise ValueError("invalid column type: {}".format(coltype))

        self._database_filename = database_filename
        self._table_name = table_name

        self._conn = sqlite3.connect(database_filename)
        self._execute(
            self._conn,
            'CREATE TABLE IF NOT EXISTS {tablename} ({cols})',
            cols=", ".join(cols))

    def _sanitize_string(self, string, what):
        if not re.match('^[a-z]+$', string):
            raise ValueError("invalid {}: {} (must be [a-z]+)".format(
                string, what))

    def _execute(self, obj, statement, *vals, **formatargs):
        formatargs['tablename'] = self._table_name
        obj.execute(statement.format(**formatargs), vals)

    def __len__(self):
        cur = self._conn.cursor()
        self._execute(cur, 'SELECT count(*) FROM {tablename}')
        return cur.fetchone()[0]


class PersistentDict(AbstractSQLContainer, collections.MutableMapping):
    def __init__(self, database_filename, table_name='persistentdict',
                 mapping={}):

        AbstractSQLContainer.__init__(self, database_filename, table_name,
                                      "key UNIQUE", "val")

        self.update(mapping)

    def __getitem__(self, key):
        cur = self._conn.cursor()
        self._execute(cur, 'SELECT val FROM {tablename} WHERE key = ?', key)

        val = cur.fetchone()

        if val is None:
            raise KeyError(key)

        return val[0]

    def __setitem__(self, key, val):
        cur = self._conn.cursor()
        with self._conn:
            if key in self:
                self._execute(
                    cur,
                    'UPDATE {tablename} SET val = ? WHERE key = ?',
                    val, key)
            else:
                self._execute(
                    cur,
                    'INSERT INTO {tablename} (key, val) VALUES (?, ?)',
                    key, val)

    def __delitem__(self, key):
        cur = self._conn.cursor()
        with self._conn:
            self._execute(cur, 'DELETE FROM {tablename} WHERE key = ?', key)
            if not cur.rowcount:
                raise KeyError(key)

    def __iter__(self):
        cur = self._conn.cursor()
        self._execute(cur, 'SELECT key FROM {tablename}')
        return iter([row[0] for row in cur])

    def __str__(self):
        return str(dict(self))

    def __repr__(self):
        return "PersistentDict({}, {}, {})".format(
            repr(self._database_filename),
            repr(self._table_name),
            repr(dict(self)))


class PersistentSet(AbstractSQLContainer, collections.MutableSet):
    def __init__(self, database_filename, table_name='persistentset',
                 collection=set()):

        AbstractSQLContainer.__init__(self, database_filename, table_name,
                                      "elem UNIQUE")

        for x in collection:
            self.add(x)

    def __contains__(self, elem):
        cur = self._conn.cursor()
        self._execute(cur, 'SELECT elem FROM {tablename} WHERE elem = ?', elem)

        return bool(cur.fetchall())

    def __iter__(self):
        cur = self._conn.cursor()
        self._execute(cur, 'SELECT elem FROM {tablename}')
        return iter([row[0] for row in cur])

    def __len__(self):
        cur = self._conn.cursor()
        self._execute(cur, 'SELECT count(*) FROM {tablename}')
        return cur.fetchone()[0]

    def add(self, elem):
        cur = self._conn.cursor()
        with self._conn:
            if elem not in self:
                self._execute(cur, 'INSERT INTO {tablename} (elem) VALUES (?)',
                              elem)

    def discard(self, elem):
        cur = self._conn.cursor()
        with self._conn:
            self._execute(cur, 'DELETE FROM {tablename} WHERE elem = ?', elem)

    def __str__(self):
        return str(set(self))

    def __repr__(self):
        return "PersistentSet({}, {}, {})".format(
            repr(self._database_filename),
            repr(self._table_name),
            repr(set(self)))
