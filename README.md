UMLS for Python
===============

These are basic tools to interact with UMLS lexica, namely UMLS, SNOMED and RxNorm, using Python 3 scripts.
For each of the three databases there are scripts (2 Bash and 1 Python) that facilitate import of the downloaded data into a local SQLite 3 database.

> You will need a UMLS license to download UMLS lexica.

For a simple start, run one of the files (`umls.py`, `snomed.py`, `rxnorm.py`) in your Shell and follow the instructions.
The scripts will prompt you to download and install the databases and, when completed, print a simple example lookup.

There are also utility scripts that offer help for specific use cases, see below.

Documentation
-------------

An [auto-generated documentation](http://chb.github.io/py-umls/) (via Sphinx) is available but not very exhaustive at the moment.
See below for some quick examples.

Usage
-----

There are `XYLookup` classes in each of the three files which can be used for database lookups (where `XY` stands for `UMLS`, `SNOMED` or `RxNorm`).
The following example code is appended to the end of the respective scripts and will be executed if you run it in the Shell.
You might want to insert `XY.check_databases()` before this code so you will get an exception if the databases haven't been set up.

    look_umls = UMLSLookup()
    code_umls = 'C0002962'
    meaning_umls = look_umls.lookup_code_meaning(code_umls)
    print('UMLS code "{0}":     {1}'.format(code_umls, meaning_umls))
    
    look_snomed = SNOMEDLookup()
    code_snomed = '215350009'
    meaning_snomed = look_snomed.lookup_code_meaning(code_snomed)
    print('SNOMED code "{0}":  {1}'.format(code_snomed, meaning_snomed))
    
    look_rxnorm = RxNormLookup()
    code_rxnorm = '328406'
    meaning_rxnorm = look_rxnorm.lookup_code_meaning(code_rxnorm, preferred=False)
    print('RxNorm code "{0}":     {1}'.format(code_rxnorm, meaning_rxnorm))

You would typically use this module as a submodule in your own project.
Best add this as a _git submodule_ but that really is up to you.
But if you do use this module as a Python module, you can't use the name `py-umls` because it contains a dash, so you must checkout this code to a correctly named directory.
I usually use `UMLS`.

Utilities
---------

### NDC Normalizer

Normalizes an NDC (National Drug Code) number.
It's built after the pseudo-code [published by NIH](http://www.nlm.nih.gov/research/umls/rxnorm/NDC_Normalization_Code.rtf), first identifies the format (e.g. "6-3-2") and then normalizes based on that finding.
The pseudocode always normalizes the NDC to 5-4-2, padded with leading zeroes and removing all dashes afterwards.
This implementation achieves the same normalization.

It also handles NDC codes that come in the "6-4" format, which usually is a 6-4-2 format with omitted package code.
Those codes first get normalized to 6-4-2 by appending "-00", then go through the standard normalization.

### rxnorm_link.py

This script precomputes ingredients, generics, treatment intents, drug classes and mechanisms of action per RxNorm concept (of specific TTYs).
The script will run for a couple of minutes but NOT STORE ANYTHING **as-is**.
You can uncomment a line that prints the generated document or do your own things, or even better:
use the script `rxnorm_link_run.sh` after you've set up your MongoDB credentials and the script will store one JSON document per RXCUI and TTY combination into a NoSQL database.
Look into `rxnorm_link_run.py` (note the file ending) where the server connections are set up and insertion happens; a Couchbase implementation is missing.

### rxnorm_graph.py

Create a graphical representation (PDF) of relationships for a given RXCUI.
You need to have `dot` installed (part of the GraphViz package).
Run the script from command line and provide a RXCUI as the first argument.
The script will then traverse the relationship graph of that concept to a specific depth (8 by default) and plot the relationships into a dot file and a PDF.
