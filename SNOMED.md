SNOMED-CT
=========

SNOMEDConcept
-------------

Holds one SNOMED concept. Its properties and methods:

### `term`

Property, uses `SNOMEDLookup().lookup_code_meaning(self.code)` to lazily fetch the concept's term.

```python
cpt = SNOMEDConcept('215350009')
print('SNOMED code "{0}":  {1}'.format(cpt.code, cpt.term))
```

### `isa()`

A method to check whether the concept has the given concept as a (direct or indirect) parent.
This looks at the 'isa' relationship (concept 116680003).

```python
cpt = SNOMEDConcept('315004001')
for other in ['128462008', '363346000', '55342001', '215350009']:
    print('SNOMED code "{0}" refines "{1}":  {2}'
        .format(cpt.code, other, cpt.isa(other)))
```


Importer
--------

The importer requires the _Release Format 2_ (RF2) files, but works with both [international](http://www.nlm.nih.gov/research/umls/licensedcontent/snomedctfiles.html) and [US](http://www.nlm.nih.gov/research/umls/Snomed/us_edition.html) releases.
