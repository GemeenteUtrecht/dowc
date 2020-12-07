======
Docker
======

For a pleasant development experience, without having to know the ins-and-outs of Django
development environments, the D.O.C. is set up to run Django dev mode with Docker.

Docker-compose
==============

The default docker-compose will initialize the database and start the development server.
The dev server automatically reloads on code changes:

.. code-block:: bash

    docker-compose up
