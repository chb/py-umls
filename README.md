UMLS for Python
===============

These are basic tools to interact with UMLS lexica, namely UMLS, SNOMED and RxNorm, using Python 3 scripts.
For each of the three databases there are scripts (2 Bash and 1 Python) that facilitate import of the downloaded data into a local SQLite 3 database.

> You will need a UMLS license to download UMLS lexica.

For a simple start, run one of the files (`umls.py`, `snomed.py`, `rxnorm.py`) in your Shell and follow the instructions.
The scripts will prompt you to download and install the databases and, when completed, print a simple example lookup.

There are also utility scripts that offer help for specific use cases, see below.

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

### rxnorm_graph.py

Create a graphical representation (PDF) of relationships for a given RXCUI.
You need to have `dot` installed (part of the GraphViz package).
Run the script from command line and provide a RXCUI as the first argument.
The script will then traverse the relationship graph of that concept to a specific depth (8 by default) and plot the relationships into a dot file and a PDF.

### rxnorm_link.py

This script precomputes ingredients, generics, treatment intents and drug classes for storage into a NoSQL database.
The script will run a while and you'll need to set up the database (MongoDB or Couchbase) in code.
