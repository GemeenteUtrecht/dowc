Document Wijzigen Component Documentation
=========================================

**Document Wijzigen Component** (short DO.W.C.) is a WebDAV server exposing documents stored in a `Documenten API <https://documenten-api.vng.cloud/>`_.

Access to documents is obtained by creating authenticated links via the DO.W.C. API endpoints. WebDAV clients, such as MS Office Word, Excel etc. are then able to read and modify (with the correct permissions) these documents. DO.W.C. is built in Python/Django.

The authentication mechanism relies on `zgw-auth-backend <https://github.com/maykinmedia/zgw-auth-backend>`_.

Please refer to this document on how to start, configure and get the DO.W.C. running yourself.

.. toctree::
   :maxdepth: 2
   :hidden:

   docker
   configuration
   frontend
   django
   mechanics
   supported_formats 


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`