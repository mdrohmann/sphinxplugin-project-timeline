Project timeline planner plugin for sphinx
==========================================

This plugin creates a project timeline out of a Sphinx_ document consisting of
several sections of project tasks.  It computes the requested time for this
project and defined milestones or deadlines.  This allows the user to stay on
top of the development tasks, and it is requires far less maintenance than
other project management tools.


Installation
------------

1. Clone this repository in a local directory with

   .. code:: bash

     git clone git@github.com:mdrohmann/sphinxplugin-project-timeline.git

2. Install the plugin (This should install all dependencies in your python
   installation automatically)

   .. code:: bash

     python setup.py install

Configuration
-------------

1. Create a new directory, say 'myprojectdir'.
2. Change into this directory and run

   .. code:: bash

     sphinx-quickstart

   and answer all the questions.  You can select the defaults if you are
   unsure.
3. Make one change in the generated file conf.py: Change the line

   .. code:: python

     extensions = []
   ..

   to

   .. code:: python

     extensions = [
       'sphinxcontrib.blockdiag',
       'sphinxplugin.projecttimeline',
     ]
   ..

Usage
-----

4. Overwrite the index.rst file with my template for the project timeline.

   .. code:: bash

     cp /path/to/plugin_repository/tests/docs/complete/index.rst .

5. Create the website with

   .. code:: bash

     make html

   and open it in your webbrowser

   .. code:: bash

     firefox _build/html/index.html

Now you can edit the index.rst and add your own tasks and update the document
as you work on them to give you a feel for the timeline of your project.  To
update, the website you have to re-do step 5 and update your browser.

.. tip::

  If you do not want to remake the website manually, you can add a watchdog_
  script, that watches the files in your project directory for changes and
  automatically re-builds the website.

.. _Sphinx: http://sphinx-doc.org/
.. _watchdoc: https://pythonhosted.org/watchdog/quickstart.html#a-simple-example
