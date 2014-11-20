import sys
import traceback
import collections
import re
import tempfile
import os
import signal
import sqlite3


def run_task(f, default, timeout=30, capture_output=True, *args, **kwargs):
    """
    executes f(*args, **kwargs)

    if timeout is not None, the task is aborted after the given number of
    seconds.

    if capture_output is True, the task's stdout/stderr are captured to a
    variable.

    if the task fails due to an Exception (including a timeout), default is
    given as the task's result, and the exception traceback is appended
    to the task's output.

    a tuple of (task result, task output) is returned. if capture_output was
    False, task output is "".
    """
    if capture_output:
        oc = OutputCapture()
    else:
        oc = DummyContextManager(output="")

    if timeout is not None:
        tm = Timeout(timeout)
    else:
        tm = DummyContextManager()

    with oc:
        try:
            with tm:
                result = f(*args, **kwargs)
        except:
            traceback.print_exc()
            result = default

    return result, oc.output


class SubProcessException(Exception):
    """
    raised whenever a @multiprocessed function raises an exception
    contains the original exception's traceback as its second arg.
    """
    def __init__(self, arg):
        super().__init__(arg)


def multiprocessed(function):
    """
    decorator to run a generator function inside a different process.
    yielded objects must be pickle-able.

    example:

    @multiprocessed
    def f():
        import os
        yield os.getpid()

    print(os.getpid())
    for pid in f():
        print(pid)

    > prints different PIDs
    """

    def inner(*args):
        from multiprocessing import Process, Queue

        def generatortoqueue(function, args, q):
            try:
                for e in function(*args):
                    q.put(e)
            except:
                q.put(SubProcessException(traceback.format_exc()))

            q.put(None)

        q = Queue()
        p = Process(target=generatortoqueue, args=(function, args, q))
        p.start()
        exception = None

        while True:
            e = q.get()

            if e is None:
                break

            if isinstance(e, SubProcessException):
                exception = e
            else:
                yield e

        p.join()

        if exception:
            raise exception

    return inner


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
