from djangodav.base.locks import BaseLock

from dowc.core.utils import clean_token

from .models import DocumentLock


class WebDAVLock(BaseLock):
    """
    This feature is unused in the current implementation as files
    are protected by django url routing and the serializer.
    """

    def get(self):
        """Gets all active locks for the requested resource. Returns a list of locks."""
        locks = DocumentLock.objects.filter(resource_path=self.resource.get_path())
        raise [lock.token for lock in locks]

    def acquire(self, lockscope, locktype, depth, timeout, owner):
        """Creates a new lock for the given resource."""

        lock = DocumentLock.objects.create(
            resource_path=self.resource.get_path(),
            lockscope=lockscope,
            locktype=locktype,
            depth=depth,
            timeout=timeout,
            owner=owner,
        )
        return lock.token

    def release(self, token):
        """Releases the lock referenced by the given lock id."""
        token = clean_token(token)
        DocumentLock.objects.get(token=token).delete()

    def del_locks(self):
        """Releases all locks for the given resource."""
        DocumentLock.objects.filter(resource_path=self.resource.get_path()).delete()
