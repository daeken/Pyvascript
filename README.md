Introduction
============

Pyvascript is an alternative syntax for Javascript.  Code can be written using 
standard Python syntax against the Javascript standard libraries.

Installation
============

Simply clone the repository.

Usage
=====

Run pyvc to precompile Pyvascript to Javascript.

Helpers
=======

The current Pyvascript helpers all depend on JQuery

 * AjaxHelper -- A base class for AJAX code, which automatically decodes a JSON response
 * TableHelper -- A base class for working with tables
 * PaginationHelper -- A base class for paginated tables.  Included in the TableHelper module

Todo
====

 * Generalize Scripts controller for Pylons and commit it.
 * Add support for user-defined macros (they exist but have to be embedded in Pyvascript itself at the moment)

Bugs
====

None known
