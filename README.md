Introduction
============

Pyvascript is an alternative syntax for Javascript.  Code can be written using 
standard Python syntax against the Javascript standard libraries.

Installation
============

Simply clone the repository.

Usage
=====

Pyvascript can be used in two ways, inline with your Python code or inside of a
template.  Examples of inline and Mako usage are included.  Support for other 
templating engines is left as an exercise for the hacker.

Helpers
=======

 * AjaxHelper -- A very simple base class for AJAX code, which automatically decodes a JSON response

Todo
====

 * Add support for $

Bugs
====

 * 'and' and 'or' in if statements break things horribly
 * When using Mako, your code is compiled at every page load
 * When using Mako, importing functions doesn't work, and you have to subclass 
   any classes you want to use
