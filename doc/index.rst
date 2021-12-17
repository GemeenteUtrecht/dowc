Document Wijzigen Component Documentation
===============================================================

**Document Wijzigen Component** (short DO.W.C.) is a WebDAV server with a Django web framework that allows for viewing and editing of documents with an MS Office WebDAV client such as MS Word, MS Excel, etc. The access to the WebDAV server is facilitated by authenticated links created in and accessed by Django. Django also takes care of authenticating the user requesting access to the document (through https://github.com/maykinmedia/zgw-auth-backend).
Please refer to this document on how to start, configure and get the DO.W.C. running yourself.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   docker
   configuration
   frontend
   django
   mechanics
   supported_formats 


Indices and tables
==================

* :ref:`docker`
* :ref:`configuration`
* :ref:`frontend`
* :ref:`django`
* :ref:`mechanics`
* :ref:`supported_formats`
