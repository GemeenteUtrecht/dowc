.. _mechanics:

Mechanics
=========

The process to open a document is as follows:

#. A POST request is made to the dowc API with the body as decribed `here <https://dowc.cg-intern.ont.utrecht.nl/api/v1/docs/#operation/documenten_create>`_. 
#. The request creates or gets a (temporary) object in the database that stores the following information:

   #. A randomly created and unique UUID.
   #. Created date.
   #. "Safe for deletion" flag.
   #. Document file.
   #. Original document's URL.
   #. Filename.
   #. Lock from DRC (in case the purpose of the request is to edit).
   #. A temporary copy of the original document.
   #. Request purpose.
   #. The user.
   #. Name change flag.
   #. A URL that points to where the request was made from.

#. The POST request from (1) returns the body that can be found `here <https://dowc.cg-intern.ont.utrecht.nl/api/v1/docs/#operation/documenten_create>`_. 
   The body contains the `magicUrl` that allows for users to view or edit the document. The `magicUrl` consists of two major components.
   
   | Part 1: Pertains to MS Office URI Scheme.
   | Part 2: URL with validation parameters and filepath to requested file.

   Part 1 is conditional. Part 2 is essential.

   In order to read/write certain files we make use of the Microsoft Office handlers
   that are installed whenever MS Office is installed.
   The handlers can be used to open files from a browser for a seamless user experience.

   For more information on the MS Office URI scheme, see this link:
   https://docs.microsoft.com/en-us/office/client-developer/office-uri-schemes.

   **Conditions for part 1 of url**

   | The requested file needs to have an extension that can be found in the :ref:`supported_formats`. If this is not the case, the file can only be opened for reading for now in the application chosen by the browser itself.
   
   **Information in part 1 of url**

   | A scheme name pertains to which particular MS Office app needs to be opened to read/write the requested file. Please see :ref:`supported_formats`.
   | A file can be read, in which case an open for view (*ofv*) command is invoked.
   | A file can be written, in which case an open for edit (*ofe*) command is invoked.


   **Information in part 2 of url**

   | *UUID*: UUID of documentfile object
   | *Token*: token created by :class:`dowc.core.tokens.DocumentTokenGenerator`
   | *Purpose*: purpose of requesting file (can be read or write)
   | *Path*: relative path to filename in webdav resource
#. The link will open the appropriate MS Office WebDAV client from the browser. 
#. If a user opened a document to read, no further actions are required. The temporary data will be deleted within 24 hours. If a user opened a document to edit, the document stays locked on the source until the user has explicitly saved the document or the edits will automatically be updated to the source within 24 hours. A notification email is sent within 24 hours to all the users and each of the documents they opened but did not explicitly save containing a link to where the document can be found and notifying them that all changes were updated at the source. The document will stay locked and unable to be edited for any other use until one of the two has happened.