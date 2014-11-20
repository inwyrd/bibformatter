bibformatter.py
==========

bibformatter.py is a Python module for automatically reformatting BibTex entries
into a canonical form. The module currently supports only inproceedings.

Features
--------
* Canonicalizes reference names to the form doe2014bibformatter
* Canonicalizes names to Jane Doe and ...
* Canonicalizes conference titles to a preconfigured list (see conferences.py)
* Removes duplicate BibTex entries

Example
-------

To format a new file:

$ bibformatter.py libraryBib.bib

This will produce invalidBib.bib and validBib.bib. Invalid entries occur when
canonicalization fails (e.g., names in the original BibTex entry were
abbreviated).

If you use crossreferences, you must first flatten the file and then process the
results:

$ bib2bib --expand --expand-xrefs -ob flattened.bib libraryBib.bib
  bibformatter.py flattened.bib

