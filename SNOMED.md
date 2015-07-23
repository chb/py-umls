SNOMED-CT
=========

SNOMEDConcept
-------------

Holds one SNOMED concept, properties and methods:

### `name`

Property, uses `SNOMEDLookup().lookup_code_meaning(self.code)` to lazily fetch the concept's term.

```python
cpt = SNOMEDConcept('215350009')
print('SNOMED code "{0}":  {1}'.format(cpt.code, cpt.term))
```

Importer
--------

The importer requires the _Release Format 2_ (RF2) files, but works with both international and US releases.
