UMLS for Python
===============

These are basic tools to interact with UMLS lexica, namely UMLS, SNOMED and
RxNorm, using Python 3 scripts. For each of the three databases there are
scripts (2 Bash and 1 Python) that facilitate import of the downloaded data
into a local SQLite 3 database.

> You will need a UMLS license to download UMLS lexica.

For a simple start, run the file `umls.py` in your Shell and follow the logged
errors until it runs through (it will prompt you to download and install the
databases). If you only want to use one of the three databases, you can be
prompted to only install the desired database as follows:

    #!/usr/bin/env python3
    
    from umls import UMLS
    
    UMLS.check_databases(['rxnorm'])

Usage
-----

This code is appended at the end of `umls.py` and will be executed if you run
it as a script. You might want to insert `UMLS.check_databases()` before this
code so you will get an exception if the databases haven't been set up.

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
