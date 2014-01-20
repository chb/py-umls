#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#	Utilities to handle UMLS
#
#	2013-01-01	Created by Pascal Pfiffner
#	2014-01-20	Extracted and converted to Python 3
#


import sys
import os.path
import logging

from sqlite import SQLite


class UMLS (object):
	""" A class for importing UMLS terminologies into an SQLite database.
	"""
	
	@classmethod
	def check_databases(cls, check=['umls', 'snomed', 'rxnorm']):
		""" Check if our databases are in place and if not, import them.
		Will raise on errors!
		
		- check: specify the databases check (defaults to all of them)
		
		UMLS: (umls.db)
		If missing prompt to use the `umls.sh` script
		
		SNOMED: (snomed.db)
		Read SNOMED CT from tab-separated files and create an SQLite database.
		
		RxNorm: (rxnorm.db)
		If missing prompt to use the `rxnorm.sh` script
		"""
		
		# UMLS
		if 'umls' in check:
			umls_db = os.path.join('databases', 'umls.db')
			if not os.path.exists(umls_db):
				raise Exception("The UMLS database at {} does not exist. Run the import script `databases/umls.sh`.".format(umls_db))
		
		# SNOMED
		if 'snomed' in check:
			snomed_db = os.path.join('databases', 'snomed.db')
			if not os.path.exists(snomed_db):
				raise Exception("The SNOMED database at {} does not exist. Run the import script `databases/snomed.py`.".format(snomed_db))
		
		# RxNorm
		if 'rxnorm' in check:
			rxnorm_db = os.path.join('databases', 'rxnorm.db')
			if not os.path.exists(rxnorm_db):
				raise Exception("The RxNorm database at {} does not exist. Run the import script `databases/rxnorm.sh`.".format(rxnorm_db))


class UMLSLookup (object):
	""" UMLS lookup """
	
	sqlite_handle = None
	did_check_dbs = False
	preferred_sources = ['"SNOMEDCT"', '"MTH"']	
	
	def __init__(self):
		self.sqlite = SQLite.get('databases/umls.db')
	
	def lookup_code(self, cui, preferred=True):
		""" Return a list with triples that contain:
		- name
		- source
		- semantic type
		by looking it up in our "descriptions" database.
		The "preferred" settings has the effect that only names from SNOMED
		(SNOMEDCD) and the Metathesaurus (MTH) will be reported. A lookup in
		our "descriptions" table is much faster than combing through the full
		MRCONSO table.
		"""
		if cui is None or len(cui) < 1:
			return []
		
		# lazy UMLS db checking
		if not UMLSLookup.did_check_dbs:
			UMLSLookup.did_check_dbs = True
			try:
				UMLS.check_databases()
			except Exception as e:
				logging.error(e)
				# should this crash and burn?
		
		# take care of negations
		negated = '-' == cui[0]
		if negated:
			cui = cui[1:]
		
		parts = cui.split('@', 1)
		lookup_cui = parts[0]
		
		# STR: Name
		# SAB: Abbreviated Source Name
		# STY: Semantic Type
		if preferred:
			sql = 'SELECT STR, SAB, STY FROM descriptions WHERE CUI = ? AND SAB IN ({})'.format(", ".join(UMLSLookup.preferred_sources))
		else:
			sql = 'SELECT STR, SAB, STY FROM descriptions WHERE CUI = ?'
		
		# return as list
		arr = []
		for res in self.sqlite.execute(sql, (lookup_cui,)):
			if negated:
				arr.append(("[NEGATED] {}".format(res[0], res[1], res[2])))
			else:
				arr.append(res)
		
		return arr
		
	
	def lookup_code_meaning(self, cui, preferred=True, no_html=True):
		""" Return a string (an empty string if the cui is null or not found)
		by looking it up in our "descriptions" database.
		The "preferred" settings has the effect that only names from SNOMED
		(SNOMEDCD) and the Metathesaurus (MTH) will be reported. A lookup in
		our "descriptions" table is much faster than combing through the full
		MRCONSO table.
		"""
		names = []
		for res in self.lookup_code(cui, preferred):
			if no_html:
				names.append("{} ({})  [{}]".format(res[0], res[1], res[2]))
			else:
				names.append("{} (<span style=\"color:#090;\">{}</span>: {})".format(res[0], res[1], res[2]))
		
		comp = ", " if no_html else "<br/>\n"
		return comp.join(names) if len(names) > 0 else ''


class SNOMEDLookup (object):
	""" SNOMED lookup """
	
	sqlite_handle = None
	
	
	def __init__(self):
		self.sqlite = SQLite.get('databases/snomed.db')
	
	def lookup_code_meaning(self, snomed_id, preferred=True, no_html=True):
		""" Returns HTML for all matches of the given SNOMED id.
		The "preferred" flag here currently has no function.
		"""
		if snomed_id is None or len(snomed_id) < 1:
			return ''
		
		sql = 'SELECT term, isa, active FROM descriptions WHERE concept_id = ?'
		names = []
		
		# loop over results
		for res in self.sqlite.execute(sql, (snomed_id,)):
			if not no_html and ('synonym' == res[1] or 0 == res[2]):
				names.append("<span style=\"color:#888;\">{}</span>".format(res[0]))
			else:
				names.append(res[0])
		
		if no_html:
			return ", ".join(names) if len(names) > 0 else ''
		return "<br/>\n".join(names) if len(names) > 0 else ''


class RxNormLookup (object):
	""" RxNorm lookup """
	
	sqlite_handle = None
	
	
	def __init__(self):
		self.sqlite = SQLite.get('databases/rxnorm.db')
	
	def lookup_code_meaning(self, rx_id, preferred=True, no_html=True):
		""" Return HTML for the meaning of the given code.
		If preferred is True (the default), only one match will be returned,
		looking for specific TTY and using the "best" one. """
		if rx_id is None or len(rx_id) < 1:
			return ''
		
		# retrieve all matches
		sql = 'SELECT STR, TTY, RXAUI FROM RXNCONSO WHERE RXCUI = ? AND LAT = "ENG"'
		found = []
		names = []
		if no_html:
			str_format = "{0} [{1}]"
		else:
			str_format = "<span title=\"RXAUI: {2}\">{0} <span style=\"color:#888;\">[{1}]</span></span>"
		
		# loop over them
		for res in self.sqlite.execute(sql, (rx_id,)):
			found.append(res)
		
		if len(found) > 0:
			
			# preferred name only
			if preferred:
				for tty in ['BN', 'IN', 'PIN', 'SBDC', 'SCDC', 'SBD', 'SCD', 'MIN']:
					for res in found:
						if tty == res[1]:
							names.append(str_format.format(res[0], res[1], res[2]))
							break
					else:
						continue
					break
				
				if len(names) < 1:
					res = found[0]
					names.append(str_format.format(res[0], res[1], res[2]))
			
			# return a list of all names
			else:
				for res in found:
					names.append(str_format.format(res[0], res[1], res[2]))
		
		if len(names) > 0:
			if no_html:
				return "; ".join(names)
			return "<br/>\n".join(names)
		return ''


# running this as a script does the database setup/check
if '__main__' == __name__:
	UMLS.check_databases()
	
	# examples
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

