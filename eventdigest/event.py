class EventSource:
    def __init__(self, name):
        self.name = name


class Event:
    def __init__(self, text, uid=None):
        """
        text:
            end-user-readable event text
        uid:
            unique identifier. if this is given, the event appears in only a
            single digests; all further events with the same UID are ignored.
        """
        self.uid = uid
        self.text = text
