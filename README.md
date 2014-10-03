Documentation Generation
========================

Update the Documentation
------------------------

1. Checkout `master` branch
2. cd to `docs`
3. execute `make html`
4. In a second clone, check out `gh-pages` branch
5. Copy all content from the master branch's `docs/_build/html` directory into the gh-pages branch (and clean up the _sources directory):

		rsync -a py-umls/docs/_build/html/ py-umls-pages/
        rm -rf py-umls-pages/_sources/
        rm py-umls-pages/objects.inv

6. Commit and push

New Modules
-----------

If there are new modules that need to be documented, just run Sphinx's apidoc generation again:

	cd py-umls/docs
	sphinx-apidoc -o . ..

Initial Setup
-------------

The initial setup that creates the `.rst` files and indexes is using `sphinx-quickstart`, so either use that or use the `-F` flag with `sphinx-apidoc`:

    cd py-umls/docs
    sphinx-apidoc -H py-umls -F -o . ..
