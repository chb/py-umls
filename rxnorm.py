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
		rxnorm_db = os.path.join(os.path.dirname(__file__), 'databases/rxnorm.db')
		if not os.path.exists(rxnorm_db):
			raise Exception("The RxNorm database at {} does not exist. Run the import script `databases/rxnorm.sh`."
				.format(os.path.abspath(rxnorm_db)))


class RxNormLookup (object):
	""" Class for RxNorm lookup. """
	
	sqlite = None
	cache_drug_class = False		# will be set to true when the prepare_to_cache_classes method gets called
	
	
	def __init__(self):
		absolute = os.path.dirname(os.path.realpath(__file__))
		self.sqlite = SQLite.get(os.path.join(absolute, 'databases/rxnorm.db'))
	
	
	# -------------------------------------------------------------------------- "name" lookup
	def lookup_rxcui(self, rxcui, preferred=True):
		""" Return a tuple with (str, tty, rxcui, rxaui) or - if "preferred" is
		False - a tuple with (preferred-name, list-of-tuples)
		"""
		if rxcui is None or len(rxcui) < 1:
			return None
		
		# retrieve all matches
		sql = 'SELECT str, tty, rxcui, rxaui FROM rxnconso WHERE rxcui = ? AND lat = "ENG"'
		
		found = []
		for res in self.sqlite.execute(sql, (rxcui,)):
			found.append(res)
		
		if 0 == len(found):
			raise Exception("RXCUI {} not found".format(rxcui))
			return None
		
		# preferred name
		pref_match = None
		for tty in ['SBDC', 'SCDC', 'SBD', 'SCD', 'CD', 'BN', 'IN', 'PIN', 'MIN']:
			for res in found:
				if tty == res[1]:
					pref_match = res
					break
			if pref_match is not None:
				break
		
		if preferred:
			return pref_match if pref_match is not None else found[0]
		
		return (pref_match[0] if pref_match is not None else None, found)
	
	def lookup_rxcui_name(self, rxcui, preferred=True, no_html=True):
		""" Return a string or HTML for the meaning of the given code.
		If preferred is True (the default), only one match will be returned,
		looking for specific TTY and using the "best" one.
		There is currently NO SUPPORT FOR preferred = False
		"""
		
		res = self.lookup_rxcui(rxcui, preferred=True)
		if rxcui is None:
			return ''
		
		if no_html:
			str_format = "{0} [{1}]"
		else:
			str_format = "<span title=\"RXAUI: {3}\">{0} <span style=\"color:#888;\">[{1}]</span></span>"
		
		return str_format.format(*res)
	
	
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
	
	def ndc_for_rxcui(self, rxcui):
		if rxcui is None:
			return None
		sql = 'SELECT ndc FROM ndc WHERE rxcui = ?'
		res = self.sqlite.executeOne(sql, (rxcui,))
		return res[0] if res else None
	
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
	def can_cache(self):
		return self.sqlite.hasTable('va_cache')
	
	def prepare_to_cache_classes(self):
		if self.sqlite.create('va_cache', '(rxcui primary key, va varchar)'):
			self.cache_drug_class = True
	
	def va_drug_class(self, rxcui):
		""" Returns a list of VA class names for a given RXCUI. EXPERIMENTAL.
		"""
		#if not self.cache_drug_class:
		#	return None		
		if rxcui is None:
			return None
		
		# check dedicated dable
		sql = 'SELECT va FROM va_cache WHERE rxcui = ?'
		res = self.sqlite.executeOne(sql, (rxcui,))
		return res[0].split('|') if res else None
	
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
	
	def fetchOne(self, sql, params=()):
		""" Execute and return the result of fetchone() on a raw SQL query. """
		return self.sqlite.execute(sql, params).fetchone()
	
	def fetchAll(self, sql, params=()):
		""" Execute and return the result of fetchall() on a raw SQL query. """
		return self.sqlite.execute(sql, params).fetchall()


class RxNormCUI (GraphableObject):
	rxcui = None
	_ttys = None
	relations = None
	rxlookup = RxNormLookup()
	
	def __init__(self, rxcui, label=None):
		super().__init__(rxcui, rxcui)
		self.shape = 'box'
		self.rxcui = rxcui
	
	@property
	def ttys(self):
		return self._ttys
	
	@ttys.setter
	def ttys(self, val):
		self._ttys = val
		self.update_shape_from_ttys()
	
	
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
			pref, found = self.rxlookup.lookup_rxcui(self.rxcui, preferred=False)
			if found is not None and len(found) > 0:
				self.ttys = set([res[1] for res in found])
				self.label = _splitted_string(pref if pref else found[0][0])
				self.label += "\n[{} - {}]".format(self.rxcui, ', '.join(sorted(self._ttys)))
			
			vas = self.rxlookup.va_drug_class(self.rxcui)
			if vas:
				self.style = 'bold'
				self.color = 'violet'
				self.label += "\n{}".format(_splitted_string(', '.join(vas)))
	
	def update_shape_from_ttys(self):
		if self._ttys:
			if 'BD' in self._ttys or 'BN' in self._ttys:
				self.style = 'bold'
			elif 'SBD' in [tty[:3] for tty in self._ttys]:
				self.shape = 'box,peripheries=2'
			elif 'MIN' in self._ttys:
				self.shape = 'polygon,sides=5,peripheries=2'
			elif 'IN' in self._ttys or 'PIN' in self._ttys:
				self.shape = 'polygon,sides=5'

class RxNormConceptRelation (GraphableRelation):
	rxcui1 = None
	rxcui2 = None
	
	def __init__(self, rxcuiobj1, rela, rxcuiobj2):
		super().__init__(rxcuiobj1, rela, rxcuiobj2)
		self.rxcui1 = rxcuiobj1
		self.rxcui2 = rxcuiobj2
		
		if 'isa' == rela[-3:]:
			self.style = 'dashed'


def _splitted_string(string, maxlen=60):
	if len(string) > maxlen:
		at = 0
		newstr = ''
		for word in string.split():
			if at > maxlen:
				newstr += "\n"
				at = 0
			if at > 0:
				newstr += ' '
				at += 1
			newstr += word
			at += len(word)
		return newstr
	return string


# running this as a script does the database setup/check
if '__main__' == __name__:
	RxNorm.check_database()
	
	# examples
	look = RxNormLookup()
	code = '328406'
	meaning = look.lookup_rxcui_name(code, preferred=False)
	dclasses = look.va_drug_class(code)
	dclass = dclasses[0] if dclasses else None
	fclasses = look.friendly_class_format(dclass)
	print('RxNorm code      "{0}":  {1}'.format(code, meaning))
	print('Drug class       "{0}":  {1}'.format(code, dclass))
	print('Friendly classes "{0}":  {1}'.format(code, fclasses))

