"""The one way a read says it could not answer."""


class SourceUnknown(Exception):  # lucidlint: ignore class-module the desk architecture names errors.py for SourceUnknown; the file is the one error type every reader raises, not a copy of the class name.
    """A read that has no answer, carrying the reason.

    Never means an empty answer: an empty list is an answer, and no reader
    returns ``None`` or ``[]`` to say "I could not tell".
    """
