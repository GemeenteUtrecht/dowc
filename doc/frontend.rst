========
Frontend
========

The frontend stack is NPM and Webpack based, which is an industry standard.

Installing your component
=========================

The recommended way to install components is to publish them as NPM packages. You can
make use of local file-system packages, or already publish them on NPM package registry.

The base idea is to run ``npm install`` in the project root:

.. code-block:: bash

    npm install --save-dev awesome-component

Development compilation
=======================

We recommend to run the frontend-stack in watch mode to automatically re-compile when
changes are made to source code:

.. code-block:: bash

    npm start

Including the component
=======================

The current configuration compiles all the frontend code into a single bundle.

The entrypoint is ``src/dowc/js/index.js``.

We recommend to add your 'component loader' in
``src/dowc/js/components/awesome-component.js``. This module is responsible for
initializing your component. Then, add the import statement to
``src/dowc/js/components/index.js``:

.. code-block:: js

    import './awesome-component.js';

Finally, build the bundle if you're not running ``npm run watch``:

.. code-block:: bash

    npm run build
