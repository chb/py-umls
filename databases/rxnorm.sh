#!/bin/sh
#
#  create an RxNORM SQLite database (and a relations triple store).
#

# our SQLite database does not exist
if [ ! -e rxnorm.db ]; then
	if [ ! -d "$1" ]; then
		echo "Provide the path to the RxNorm directory as first argument when invoking this script. Download the latest version here: http://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html"
		exit 1
	fi
	if [ ! -d "$1/rrf" ]; then
		echo "There is no directory named rrf in the directory you provided. Download the latest version here: http://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html"
		exit 1
	fi
	
	# init the database
	cat "$1/scripts/mysql/Table_scripts_mysql_rxn.sql" | sqlite3 rxnorm.db
	
	# convert RRF files (strip last pipe and remove quote (") characters, those are giving SQLite troubles)
	if [ ! -e "$1/rrf/RXNREL.pipe" ]; then
		current=$(pwd)
		cd "$1/rrf"
		echo "-> Converting RRF files for SQLite"
		for f in *.RRF; do
			sed -e 's/.$//' -e 's/"//g' "$f" > "${f%RRF}pipe"
		done
		cd $current
	fi
	
	# import tables
	for f in "$1/rrf/"*.pipe; do
		table=$(basename ${f%.pipe})
		echo "-> Importing $table"
		sqlite3 rxnorm.db ".import '$f' '$table'"
	done
	
	# create an NDC table
	echo "-> Creating NDC table"
	# sqlite3 rxnorm.db "CREATE TABLE NDC AS SELECT RXCUI, ATV AS NDC FROM RXNSAT WHERE ATN = 'NDC';"	# we do it in 2 steps to create the primary index column
	sqlite3 rxnorm.db "CREATE TABLE NDC (RXCUI INT, NDC VARCHAR);"
	sqlite3 rxnorm.db "INSERT INTO NDC SELECT RXCUI, ATV FROM RXNSAT WHERE ATN = 'NDC';"
	sqlite3 rxnorm.db "CREATE INDEX X_RXCUI ON NDC (RXCUI);"
	sqlite3 rxnorm.db "CREATE INDEX X_NDC ON NDC (NDC);"
	
	# some SQLite gems
	## export NDC to CSV
	# SELECT RXCUI, NDC FROM NDC INTO OUTFILE 'ndc.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY "\n";
	## export RxNorm-only names with their type (TTY) to CSV
	# SELECT RXCUI, TTY, STR FROM RXNCONSO WHERE SAB = 'RXNORM' INTO OUTFILE 'names.csv' FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY "\n";
fi

# dump to N-Triples
exit 0
sqlite3 rxnorm.db <<SQLITE_COMMAND
.headers OFF
.separator ""
.mode list
.out rxnorm.nt
SELECT "<http://purl.bioontology.org/ontology/RXNORM/", RXCUI2, "> <http://purl.bioontology.org/ontology/RXNORM#", RELA, "> <http://purl.bioontology.org/ontology/RXNORM/", RXCUI1, "> ." FROM RXNREL WHERE RELA != '';
SQLITE_COMMAND

