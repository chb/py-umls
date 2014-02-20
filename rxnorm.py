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
from graphable import GraphableObject, GraphableRelation


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
	
	
	# -------------------------------------------------------------------------- "name" lookup
	def lookup_rxcui(self, rxcui, preferred=True):
		""" Return a tuple with (str, tty, rxcui, rxaui) or a list of tuples if
		"preferred" is False.
		"""
		if rxcui is None or len(rxcui) < 1:
			return ''
		
		# retrieve all matches
		sql = 'SELECT str, tty, rxcui, rxaui FROM rxnconso WHERE rxcui = ? AND lat = "ENG"'
		
		found = []
		for res in self.sqlite.execute(sql, (rxcui,)):
			found.append(res)
		
		if 0 == len(found):
			raise Exception("RXCUI {} not found".format(rxcui))
			return None
		
		if preferred:
			for tty in ['BN', 'IN', 'PIN', 'SBDC', 'SCDC', 'SBD', 'SCD', 'MIN']:
				for res in found:
					if tty == res[1]:
						return res
			return found[0]
		
		return found
	
	def lookup_rxcui_name(self, rxcui, preferred=True, no_html=True):
		""" Return a string or HTML for the meaning of the given code.
		If preferred is True (the default), only one match will be returned,
		looking for specific TTY and using the "best" one. """
		if rxcui is None or len(rxcui) < 1:
			return ''
		
		# TODO: use self.lookup_rxcui()
		# retrieve all matches
		sql = 'SELECT STR, TTY, RXAUI FROM RXNCONSO WHERE RXCUI = ? AND LAT = "ENG"'
		found = []
		names = []
		if no_html:
			str_format = "{0} [{1}]"
		else:
			str_format = "<span title=\"RXAUI: {2}\">{0} <span style=\"color:#888;\">[{1}]</span></span>"
		
		# loop over them
		for res in self.sqlite.execute(sql, (rxcui,)):
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
		
		sql = 'SELECT tty FROM rxnconso WHERE rxcui = ?'
		ttys = set()
		for res in self.sqlite.execute(sql, (rxcui,)):
			ttys.add(res[0])
		
		return ttys
	
	def lookup_related(self, rxcui, relation=None, to_rxcui=None):
		""" Returns a set of tuples containing the RXCUI and the actual relation
		for the desired relation, or all if the relation is not specified.
		"""
		if rxcui is None:
			return None
		
		found = set()
		if relation is not None:
			sql = "SELECT rxcui1, rela FROM rxnrel WHERE rxcui2 = ? AND rela = ?"
			for res in self.sqlite.execute(sql, (rxcui, relation)):
				found.add(res)
		elif to_rxcui is not None:
			sql = "SELECT rxcui1, rela FROM rxnrel WHERE rxcui2 = ? AND rxcui1 = ?"
			for res in self.sqlite.execute(sql, (rxcui, to_rxcui)):
				found.add(res)
		else:
			sql = "SELECT rxcui1, rela FROM rxnrel WHERE rxcui2 = ?"
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


	# -------------------------------------------------------------------------- Drug Class OBSOLETE, WILL BE GONE
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
			return None
		
		if rxcui == for_rxcui:
			logging.debug('-->  Checking relations for {}, has TTYs: {}'.format(rxcui, ', '.join(ttys)))
		else:
			logging.debug('-->  Checking relations for {} (for {}), has TTYs: {}'.format(rxcui, for_rxcui, ', '.join(ttys)))
		
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
		
		# cache; the main rxcui even if not found
		if res is not None:
			self._cache_va_drug_class(rxcui, for_rxcui, res[0])
			if for_rxcui is not None and for_rxcui != rxcui:
				self._cache_va_drug_class(for_rxcui, for_rxcui, res[0])
			
			logging.debug('-->  Found class for {} in {}'.format(for_rxcui, rxcui))
			return res[0]
		
		self._cache_va_drug_class(rxcui, for_rxcui, None)
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


class RxNormCUI (GraphableObject):
	rxcui = None
	_tty = None
	relations = None
	rxlookup = RxNormLookup()
	
	def __init__(self, rxcui, label=None):
		super().__init__(rxcui, rxcui)
		self.shape = 'box'
		self.rxcui = rxcui
	
	@property
	def tty(self):
		return self._tty
	
	@tty.setter
	def tty(self, val):
		self._tty = val
		self.update_shape_from_tty()
	
	
	def find_relations(self, to_rxcui=None, max_width=10):
		counted = {}
		for rxcui, rela in self.rxlookup.lookup_related(self.rxcui, None, to_rxcui):
			if rela in counted:
				counted[rela].append(rxcui)
			else:
				counted[rela] = [rxcui]
		
		found = []
		for rela, items in sorted(counted.items()):		# sort to generate mostly consistent dot files
			if len(items) > max_width:
				proxy = GraphableObject(None, rela)
				rel = GraphableRelation(self, str(len(items)), proxy)
				
				if self.announced_via:					# if our announcer is here, be nice and link back
					for rxcui in items:
						if rxcui == self.announced_via.rxcui1.rxcui:
							via = RxNormCUI(rxcui)
							found.append(RxNormConceptRelation(self, rela, via))
			else:
				for rxcui in sorted(items):				# sort to generate mostly consistent dot files
					obj = RxNormCUI(rxcui)
					rel = RxNormConceptRelation(self, rela, obj)
			found.append(rel)
		
		return found
	
	
	def deliver_to(self, dot_context, is_leaf):
		self.update_self_from_rxcui()
		super().deliver_to(dot_context, is_leaf)
		
		# if we are a leaf, still fetch the relation going back to our announcer
		if is_leaf:
			if self.relations is None and self.announced_via:
				rela = self.find_relations(
					to_rxcui=self.announced_via.rxcui1.rxcui,
					max_width=dot_context.max_width
				)
				if rela:
					rela[0].announce_to(dot_context)
		else:
			if self.relations is None:
				self.relations = self.find_relations(max_width=dot_context.max_width)
			
			for rel in self.relations:
				rel.announce_to(dot_context)
	
	
	def update_self_from_rxcui(self):
		if self.rxcui:
			res = self.rxlookup.lookup_rxcui(self.rxcui)
			self.label = "{0}\n[{2} {1}]".format(*res)
			self.tty = res[1]
	
	def update_shape_from_tty(self):
		if self._tty:
			if 'IN' == self._tty[-2:]:
				self.shape = 'polygon,sides=5'
				if 'MIN' == self._tty:
					self.shape += ',peripheries=2'
			elif 'BD' == self._tty or 'BN' == self._tty:
				self.shape = 'polygon,sides=4,skew=.4'
			elif 'SCD' == self._tty[:3]:
				self.shape = 'box,peripheries=2'

class RxNormConceptRelation (GraphableRelation):
	rxcui1 = None
	rxcui2 = None
	
	def __init__(self, rxcuiobj1, rela, rxcuiobj2):
		super().__init__(rxcuiobj1, rela, rxcuiobj2)
		self.rxcui1 = rxcuiobj1
		self.rxcui2 = rxcuiobj2
		
		if 'isa' == rela[-3:]:
			self.style = 'dashed'


# running this as a script does the database setup/check
if '__main__' == __name__:
	RxNorm.check_database()
	
	# examples
	look = RxNormLookup()
	code = '328406'
	meaning = look.lookup_rxcui_name(code, preferred=False)
	dclass = look.find_va_drug_class(code)
	fclasses = look.friendly_class_format(dclass)
	print('RxNorm code      "{0}":  {1}'.format(code, meaning))
	print('Drug class       "{0}":  {1}'.format(code, dclass))
	print('Friendly classes "{0}":  {1}'.format(code, fclasses))

