from djangodav.acls import DavAcl


class ReadAndWriteOnlyAcl(DavAcl):
    def __init__(self, read=True, write=True, delete=False, full=None):
        super().__init__(read, write, delete, full)
