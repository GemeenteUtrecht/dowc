======
Dowc
======

:Version: 0.1.0
:Source: https://github.com/GemeenteUtrecht/dowc
:Keywords: ``documents``, ``zaakgericht werken``
:PythonVersion: 3.8

Dowc (DOcument Wijzigen Component) facilitates local viewing and editing of non-local MS Office documents. 


Introduction
============

Zaken in Open Zaak can have relevant documents. End-users of the ZAC, for example, need to be able to read and edit these documents provided they have the appropriate permissions. Viewing and editing should happen in their local installation of MS Office.

The dowc provides the machinery to facilitate:

* local viewing, and
* local editing of non-local MS Office documents.

Limitations
============
Documents will need to be explicitly saved through a separate POST request https://dowc.cg-intern.ont.utrecht.nl/api/v1/docs/#operation/documenten_destroy. If this isn't done for every document that was opened, a notification will be sent within 24 hours and the document will be closed with all updates pushed to the source document.
There is currently also no way to abort the editing action outside of the normal MS Office methods of undoing work.


Documentation
=============

See ``INSTALL.rst`` for installation instructions, available settings and
commands.
See ``doc/mechanics.rst`` for a brief explanation of the mechanics of dowc.
See ``doc/supported_formats.rst`` for a list of file formats currently supported.

References
==========

* `Issues <https://github.com/GemeenteUtrecht/dowc/issues>`_
* `Code <https://github.com/GemeenteUtrecht/dowc>`_
