RxNorm
======

(Should add some examples on how to work with RxNorm here)

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
