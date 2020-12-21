Installation
============

Add ``senaite.ast`` in the eggs section of your buildout:

.. code-block:: ini

    eggs =
        ...
        senaite.ast

Run ``bin/buildout`` afterwards. With this configuration, buildout will
download and install the latest published release of `senaite.ast from Pypi`_,
as well as `senaite.microorganism`_ and `senaite.abx`_ if not yet installed.

Once buildout finishes, start the instance, login with a user with "Site
Administrator" privileges and activate the add-on:

http://localhost:8080/senaite/prefs_install_products_form

.. note:: It assumes you have a SENAITE zeo client listening to port 8080


.. Links

.. _senaite.ast from Pypi: https://pypi.org/project/senaite.ast
.. _senaite.microorganism: https://pypi.org/project/senaite.microorganism
.. _senaite.abx: https://pypi.org/project/senaite.abx
