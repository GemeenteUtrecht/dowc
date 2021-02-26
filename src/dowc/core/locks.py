import uuid
from djangodav.base.locks import BaseLock


class WebDAVLock(BaseLock):
    """
    This feature is unused in the current implementation as files
    are protected by django url routing and the serializer.
    """
    def acquire(self, lockscope, locktype, depth, timeout, owner):
        """
        Returns random uuid to satisfy WebDAV client.
        """
        # TODO: ACTUALLY LOCK THE FILE
        return uuid.uuid4()

    def release(self, token):
        """
        Always returns True in current implementation.
        """
        return True
