from django.shortcuts import render

from sendfile import sendfile


def get_document(request):
    pass
    # download = get_object_or_404(Download, pk=download_id)
    # if download.is_public:
    #     return sendfile(request, download.file.path)
    # return _auth_download(request, download)
