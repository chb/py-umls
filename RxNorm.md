RxNorm
======

The `RxNormLookup` class can be used for database lookups, an example is shown below.
Similar code is also appended to the end of `rxnorm.py` and executed if you simply run the file in the Shell.
You might want to insert `RxNorm.check_databases()` before this code so you will get an exception if the databases haven't been set up.

```python
look = RxNormLookup()
rxcui = '328406'
meaning = look.lookup_code_meaning(rxcui, preferred=False)
related = look.lookup_related(rxcui)
print('RxCUI          "{0}":  {1}'.format(rxcui, meaning))
for rrxcui, rrela in sorted(related, key=lambda x: x[1]):
	rname, rtty, a, b = look.lookup_rxcui(rrxcui)
	print('  {}:  {} {}  {}'.format(rrela, rrxcui, rtty, rname))
```
---

```
RxCUI          "328406":  Methotrexate 25 MG/ML [SCDC]
Relationships  "328406":
            constitutes:  1655956   SCD  40 ML Methotrexate 25 MG/ML Injection
            constitutes:  1655960   SCD  2 ML Methotrexate 25 MG/ML Injection
            constitutes:  1655967   SCD  4 ML Methotrexate 25 MG/ML Injection
            constitutes:  1655968   SCD  8 ML Methotrexate 25 MG/ML Injection
            constitutes:  1441402   SCD  0.4 ML Methotrexate 25 MG/ML Auto-Injector
            constitutes:  1441409   SBD  Methotrexate 25 MG/ML Auto-Injector [Otrexup]
            constitutes:  1655957   SCD  Methotrexate 25 MG/ML Injection
            constitutes:  1441407   SBD  0.4 ML Methotrexate 25 MG/ML Auto-Injector [Otrexup]
            constitutes:  1441408   SCD  Methotrexate 25 MG/ML Auto-Injector
            constitutes:  1655959   SCD  10 ML Methotrexate 25 MG/ML Injection
         has_ingredient:     6851    BN  Methotrexate
          has_tradename:  1441404  SBDC  Methotrexate 25 MG/ML [Otrexup]
```

Utilities
---------

### NDC Normalizer

Normalizes an NDC (National Drug Code) number.
It's built after the pseudo-code [published by NIH](http://www.nlm.nih.gov/research/umls/rxnorm/NDC_Normalization_Code.rtf), first identifies the format (e.g. "6-3-2") and then normalizes based on that finding.
The pseudocode always normalizes the NDC to 5-4-2, padded with leading zeroes and removing all dashes afterwards.
This implementation achieves the same normalization.

It also handles NDC codes that come in the "6-4" format, which usually is a 6-4-2 format with omitted package code.
Those codes first get normalized to 6-4-2 by appending "-00", then go through the standard normalization.

```python
RxNorm.ndc_normalize('000074-1486-14')  # '00074148614'
RxNorm.ndc_normalize('012579-*056')     # '12579005600'
RxNorm.ndc_normalize('057982-987-9')    # '57982098709'
...
```

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

```python
python rxnorm_graph.py 328406
```

