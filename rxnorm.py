#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#	Utilities to handle RxNorm
#
#	2014-01-28	Extracted from UMLS.py

import sys
import os.path
sys.path.insert(0, os.path.dirname(__file__))

import logging
import re
from collections import Counter, OrderedDict
from sqlite import SQLite


class RxNorm (object):
	""" A class for handling RxNorm in an SQLite database.
	"""
	
	@classmethod
	def check_database(cls):
		""" Check if our database is in place and if not, import them.
		Will raise on errors!
		
		RxNorm: (rxnorm.db)
		If missing prompt to use the `rxnorm.sh` script
		"""
		
		# RxNorm
		rxnorm_db = os.path.join('databases', 'rxnorm.db')
		if not os.path.exists(rxnorm_db):
			raise Exception("The RxNorm database at {} does not exist. Run the import script `databases/rxnorm.sh`."
				.format(os.path.abspath(rxnorm_db)))


class RxNormLookup (object):
	""" Class for RxNorm lookup. """
	
	sqlite = None
	cache_drug_class = False		# will be set to true if the prepare_to_cache_classes method gets called
	
	
	def __init__(self):
		absolute = os.path.dirname(os.path.realpath(__file__))
		self.sqlite = SQLite.get(os.path.join(absolute, 'databases/rxnorm.db'))
	
	
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
		return None
	
	
	# -------------------------------------------------------------------------- Relations
	def lookup_tty(self, rxcui):
		""" Returns a set of TTYs for the given RXCUI. """
		if rxcui is None:
			return None
		
		sql = 'SELECT TTY FROM RXNCONSO WHERE RXCUI = ?'
		ttys = set()
		for res in self.sqlite.execute(sql, (rxcui,)):
			ttys.add(res[0])
		
		return ttys
	
	def lookup_related(self, rxcui, relation=None):
		""" Returns a set of tuples containing the RXCUI and the actual relation
		for the desired relation, or all if the relation is not specified.
		"""
		if rxcui is None:
			return None
		
		found = set()
		if relation is not None:
			sql = "SELECT RXCUI2, RELA FROM RXNREL WHERE RXCUI1 = ? AND RELA = ?"
			for res in self.sqlite.execute(sql, (rxcui, relation)):
				found.add(res)
		else:
			sql = "SELECT RXCUI2, RELA FROM RXNREL WHERE RXCUI1 = ?"
			for res in self.sqlite.execute(sql, (rxcui,)):
				found.add(res)
		
		return found
	
	
	# -------------------------------------------------------------------------- RxCUI
	def rxcui_for_ndc(self, ndc):
		if ndc is None:
			return None
		# TODO: ensure NDC normalization
		
		rxcuis = {}
		sql = "SELECT RXCUI FROM NDC WHERE NDC = ?"
		for res in self.sqlite.execute(sql, (ndc,)):
			rxcuis[res[0]] = rxcuis.get(res[0], 0) + 1
		
		if len(rxcuis) < 2:
			return list(rxcuis.keys())[0] if len(rxcuis) > 0 else None
		
		popular = OrderedDict(Counter(rxcuis).most_common())
		return popular.popitem(False)[0]
	
	def rxcui_for_name(self, name):
		if name is None:
			return None
		
		rxcuis = {}
		
		# try the full string, allowing wildcard at the trailing end
		sql = 'SELECT RXCUI FROM RXNCONSO WHERE STR LIKE ?'
		for res in self.sqlite.execute(sql, (name + '%',)):
			rxcuis[res[0]] = rxcuis.get(res[0], 0) + 1
		
		# nothing yet, try chopping off parts from the right
		if 0 == len(rxcuis):
			parts = name.split()
			for x in range(len(parts) - 1):
				comp = ' '.join(parts[:-(x+1)])
				for res in self.sqlite.execute(sql, (comp + '%',)):
					rxcuis[res[0]] = rxcuis.get(res[0], 0) + 1
				if len(rxcuis) > 0:
					break
		
		if len(rxcuis) < 2:
			return list(rxcuis.keys())[0] if len(rxcuis) > 0 else None
		
		popular = OrderedDict(Counter(rxcuis).most_common())
		return popular.popitem(False)[0]


	# -------------------------------------------------------------------------- Drug Class
	def prepare_to_cache_classes(self):
		if self.sqlite.create('drug_class_cache', '(rxcui primary key, rxcui_orig int, VA varchar)'):
			self.cache_drug_class = True
	
	
	def find_va_drug_class(self, rxcui, for_rxcui=None, until_found=False):
		""" Executes "_find_va_drug_class" on the given rxcui, then
		"_find_va_drug_class" on all immediate related concepts in order to
		find a drug class.
		If "until_found" is true, recurses on all relations of the immediate
		relations until a class is found or there are no more relations (!!).
		"""
		if rxcui is None:
			return None
		if for_rxcui is None:
			for_rxcui = rxcui
		
		dclass = self._find_va_drug_class(rxcui, for_rxcui)
		if dclass is not None:
			return dclass
		
		# no direct class, check first grade relations
		ttys = self.lookup_tty(rxcui)
		if ttys is None or 0 == len(ttys):
			self._cache_va_drug_class(rxcui, rxcui, None)
			return None
		
		logging.debug('-->  Checking relations for {}, has TTYs: {}'.format(rxcui, ', '.join(ttys)))
		
		priority = [
			'has_tradename',
			'part_of',
			'consists_of',
			'has_dose_form',
			'has_ingredient',
			'isa'
		]
		mapping = {
			'has_tradename': ['BD', 'CD', 'DP', 'SBD', 'SY'],
			'part_of': ['IN', 'MIN', 'FN', 'PT'],
			'consists_of': ['SBDC', 'SCDC', 'TMSY'],
			'has_dose_form': ['CD', 'DF', 'FN', 'PT'],
			'has_ingredient': ['BN', 'FN', 'MH', 'N1', 'PEN', 'PM', 'PT', 'SU', 'SY'],
			'isa': ['SCDG', 'TMSY']
		}
		
		for relation in priority:
			mapped = set(mapping[relation])
			if ttys & mapped:
				
				# lookup desired relations for this TTY
				relas = self.lookup_related(rxcui, relation)
				if relas is not None:
					for rel_rxcui, rel_rela in relas:
						
						# lookup class for relation
						if until_found:
							dclass = self.find_va_drug_class(rel_rxcui, for_rxcui, until_found)
						else:
							dclass = self._find_va_drug_class(rel_rxcui, for_rxcui)
						
						if dclass is not None:
							break
			if dclass is not None:
				break
		
		return dclass
	
	def _find_va_drug_class(self, rxcui, for_rxcui):
		""" Tries to find the VA drug class in RXNSAT for the given RXCUI.
		- rxcui The RXCUI to seek a drug class for
		- for_rxcui The original RXCUI for which a drug class is being seeked
		"""
		if rxcui is None:
			return None
		
		# is it cached?
		dclass = self._lookup_cached_va_drug_class(rxcui)
		if dclass is not None:
			return dclass
		
		# look in RXNSAT table
		sql = 'SELECT ATV FROM RXNSAT WHERE RXCUI = ? AND ATN = "VA_CLASS_NAME"'
		res = self.sqlite.executeOne(sql, (rxcui,))
		
		# cache if found
		if res is not None:
			logging.debug('-->  Found class for {} in {}'.format(for_rxcui, rxcui))
			if for_rxcui is not None and for_rxcui != rxcui:
				self._cache_va_drug_class(for_rxcui, for_rxcui, res[0])
			self._cache_va_drug_class(rxcui, for_rxcui, res[0])
			
			return res[0]
		
		return None
	
	
	def _lookup_cached_va_drug_class(self, rxcui):
		""" Returns the VA class name (the first one found) for a given RXCUI.
		"""
		if not self.cache_drug_class:
			return None		
		if rxcui is None:
			return None
		
		# check dedicated dable
		sql = 'SELECT VA FROM drug_class_cache WHERE rxcui = ?'
		res = self.sqlite.executeOne(sql, (rxcui,))
		return res[0] if res else None

	def _cache_va_drug_class(self, rxcui, original_rxcui, va_class):
		""" Caches the given va_class as drug class for rxcui.
		
		- rxcui: the RXCUI to assign this class for
		- original_rxcui: the RXCUI this class is originally assigned to
		- va_class: the class name
		"""
		if not self.cache_drug_class:
			return
		
		if rxcui is None:
			logging.error("You must provide the RXCUI to store its class")
			return
		
		sql = '''INSERT OR REPLACE INTO drug_class_cache
				 (rxcui, rxcui_orig, VA) VALUES (?, ?, ?)'''
		for_rxcui = original_rxcui if rxcui != original_rxcui else None
		insert_id = self.sqlite.executeInsert(sql, (rxcui, for_rxcui, va_class))
		
		if insert_id > 0:
			self.sqlite.commit()
		else:
			self.sqlite.rollback()
	
	
	def _friendly_va_drug_classes(self, va_name):
		""" Looks up the friendly class names for the given original VA drug
		class name.
		"""
		if va_name is None:
			return None
		
		if '[' != va_name[0] or ']' not in va_name:
			logging.error("Invalid VA class name: {}".format(va_name))
			return None
		
		names = []
		code = va_name[1:va_name.index(']')]
		sql = "SELECT FRIENDLY FROM FRIENDLY_CLASS_NAMES WHERE VACODE = ?"
		for res in self.sqlite.execute(sql, (code,)):
			names.append(res[0])
		
		return names if len(names) > 0 else None
	
	def friendly_class_format(self, va_name):
		""" Tries to reformat the VA drug class name so it's suitable for
		display.
		"""
		if va_name is None or 0 == len(va_name):
			return None
		
		# remove identifier
		if ']' in va_name:
			va_name = va_name[va_name.index(']')+1:]
			va_name = va_name.strip()
		
		# remove appended specificiers
		if ',' in va_name and va_name.index(',') > 2:
			va_name = va_name[0:va_name.index(',')]
		
		if '/' in va_name and va_name.index('/') > 2:
			va_name = va_name[0:va_name.index('/')]
		
		# capitalize nicely
		va_name = va_name.lower();
		va_name = re.sub(r'(^| )(\w)', lambda match: r'{}{}'.format(match.group(1), match.group(2).upper()), va_name)
		
		return va_name
	
	
	# -------------------------------------------------------------------------- Bare Metal
	def execute(self, sql, params=()):
		""" Execute and return the pointer of an SQLite execute() query. """
		return self.sqlite.execute(sql, params)
	
	def fetchAll(self, sql, params=()):
		""" Execute and return the result of fetchall() on a raw SQL query. """
		return self.sqlite.execute(sql, params).fetchall()


# running this as a script does the database setup/check
if '__main__' == __name__:
	RxNorm.check_database()
	
	# examples
	look = RxNormLookup()
	code = '328406'
	meaning = look.lookup_code_meaning(code, preferred=False)
	dclass = look.find_va_drug_class(code)
	fclasses = look.friendly_class_format(dclass)
	print('RxNorm code      "{0}":  {1}'.format(code, meaning))
	print('Drug class       "{0}":  {1}'.format(code, dclass))
	print('Friendly classes "{0}":  {1}'.format(code, fclasses))

