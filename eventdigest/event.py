class EventSource:
    def __init__(self, name):
        self.name = name


class Event:
    def __init__(self, short, uid=None, full=None, raw=None):
        """
        short:
            one-line end-user-readable text representation
        uid:
            unique identifier. if this is given, the event appears in only a
            single digests; all further events with the same UID are ignored.
        full:
            multi-line representation. defaults to short.
        raw:
            any raw python object.
        """
        self.uid = uid
        self.short = short
        if not full:
            full = short
        self.full = full
        self.raw = raw

    def __str__(self):
        return self.short

    def __repr__(self):
        return "Event(uid=%s, short=%s)" % (repr(self.uid), repr(self.short))

    def __equals__(self, other):
        if not isinstance(other, Event):
            return False

        if not self.uid:
            return self is other

        return self.uid == other.uid
