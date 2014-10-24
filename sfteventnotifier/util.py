import signal
import tempfile
import os


class CommandFailedException(Exception):
    pass


def run_task(f, timeout=30, capture_output=True, *args, **kwargs):
    oc = OutputCapture() if capture_output else DummyContextManager(output="")
    try:
        with oc:
            with Timeout(timeout) if timeout else DummyContextManager():
                result = f(*args, **kwargs)
    except Exception as e:
        raise CommandFailedException(oc.output) from e

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
