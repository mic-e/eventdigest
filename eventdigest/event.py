class Event:
    def __init__(self, source, uid, short, full=None, raw=None):
        """
        source:
            the event source (a string, e.g. "HBCI")
        uid:
            unique identifier
        short:
            one-line end-user-readable text representation
        full:
            multi-line representation, in Markdown format
        raw:
            any raw python object
        """
        self.source = source
        self.uid = ":".join((source, uid))
        self.pure_uid = uid
        self.short = short
        if not full:
            full = short
        self.full = full
        self.raw = raw

    def __str__(self):
        return self.short

    def __repr__(self):
        return "Event(uid=%s, source=%s, short=%s)" % (
            repr(self.pure_uid),
            repr(self.source),
            repr(self.short))

    def __equals__(self, other):
        if not isinstance(other, Event):
            return False

        return self.uid == other.uid
