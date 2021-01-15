from django.core import signing

from djangodav.base.locks import BaseLock


class WebDAVLock(BaseLock):
    def acquire(self, lockscope, locktype, depth, timeout, owner):
        # TODO: ACTUALLY LOCK THE FILE
        # For now creating a token out of given arguments and secret key.
        token = signing.dumps(
            {
                "lockscope": lockscope,
                "locktype": locktype,
                "depth": depth,
                "timeout": timeout,
                "owner": owner,
            }
        )
        return token

    def release(self, token):
        # TODO: ACTUALLY RELEASE THE FILE
        data_dict = signing.loads(token)

        # For now adding some pseudo checks for testing purposes.
        req_dict_fields = ["lockscope", "locktype", "depth", "timeout", "owner"]
        if all([req_field in data_dict.keys() for req_field in req_dict_fields]):
            return True

        else:
            return False
