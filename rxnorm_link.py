#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#	Precompute and store interesting RXCUI relationships
#
#	2012-09-28	Created by Josh Mandel
#	2014-02-10	Stolen by Pascal Pfiffner
#
#	For profiling: pycallgraph graphviz -- rxnorm_link.py

import sys
import os.path
sys.path.insert(0, os.path.dirname(__file__))

import json
import signal
import logging
import couchbase
from datetime import datetime

from rxnorm import RxNorm, RxNormLookup


def doQ(rxhandle, q, p):
	return [x[0] for x in rxhandle.fetchAll(q, p)]

def toBrandAndGeneric(rxhandle, rxcuis, tty):
	ret = set()
	for rxcui in rxcuis:
		ret.update(doQ(rxhandle, "SELECT rxcui1 from rxnrel where rxcui2=? and rela='tradename_of'", (rxcui,)))
	return ret

def toComponents(rxhandle, rxcuis, tty):
	ret = set()

	if tty not in ("SBD", "SCD"):
		return ret

	for rxcui in rxcuis:
		cs = doQ(rxhandle, "SELECT rxcui1 from rxnrel where rxcui2=? and rela='consists_of'", (rxcui,))
		for c in cs:
			ret.update(doQ(rxhandle, "SELECT rxcui from rxnconso where rxcui=? and sab='RXNORM' and tty='SCDC'", (c,)))        

	return ret

def toTreatmentIntents(rxhandle, rxcuis, tty):
	ret = set()
	for rxcui in rxcuis:
		ret.update(toTreatmentIntents_helper(rxhandle, rxcui, tty))
	return ret

def toTreatmentIntents_helper(rxhandle, rxcui, tty):
	assert tty=='IN'
	ret = []
	rxauis = doQ(rxhandle, "SELECT rxaui from rxnconso where rxcui=? and tty='FN' and sab='NDFRT'", (rxcui,))
	for a in rxauis:
		a1 = doQ(rxhandle, "SELECT rxaui1 from rxnrel where rxaui2=? and rela='may_treat'", (a,))
		if len(a1) > 0:
			dz = doQ(rxhandle, "SELECT str from rxnconso where rxaui=? and tty='FN' and sab='NDFRT'", (a1[0],))
			dz = map(lambda x: x.replace(" [Disease/Finding]", ""), dz)
			ret.extend(dz)
	return ret

def toMechanism(rxhandle, rxcuis, tty):
	ret = set()
	for v in rxcuis:
		ret.update(toMechanism_helper(rxhandle, v, tty))
	return ret

def toMechanism_helper(rxhandle, rxcui, tty):
	assert tty=='IN'
	ret = set()
	rxauis = doQ(rxhandle, "SELECT rxaui from rxnconso where rxcui=? and tty='FN' and sab='NDFRT'", (rxcui,))
	for a in rxauis:
		a1 = doQ(rxhandle, "SELECT rxaui1 from rxnrel where rxaui2=? and rela='has_mechanism_of_action'", (a,))
		if len(a1) > 0:
			moa = doQ(rxhandle, "SELECT str from rxnconso where rxaui=? and tty='FN' and sab='NDFRT'", (a1[0],))
			moa = map(lambda x: x.replace(" [MoA]", ""), moa)
			ret.update(moa)
	return ret


def toIngredients(rxhandle, rxcuis, tty):
	ret = set()
	for v in rxcuis:
		ret.update(toIngredients_helper(rxhandle, v, tty))
	return ret

def toIngredients_helper(rxhandle, rxcui, tty):
	if 'IN' == tty:
		return []
	
	# can lookup ingredient directly
	map_direct = {
		'MIN': 'has_part',
		'PIN': 'form_of',
		'BN': 'tradename_of',
		'SCDC': 'has_ingredient',
		'SCDF': 'has_ingredient',
		'SCDG': 'has_ingredient',
	}
	
	if tty in map_direct:
		return doQ(rxhandle, "SELECT rxcui1 from rxnrel where rxcui2=? and rela=?", (rxcui, map_direct[tty]))
	
	# indirect ingredient lookup
	map_indirect = {
		'BPCK': ('contains', 'SCD'),
		'GPCK': ('contains', 'SCD'),
		'SBD': ('tradename_of', 'SCD'),
		'SBDC': ('tradename_of', 'SCDC'),
		'SBDF': ('tradename_of', 'SCDF'),
		'SBDG': ('tradename_of', 'SCDG'),
		'SCD': ('consists_of', 'SCDC'),
	}
	
	if tty in map_indirect:
		val = map_indirect[tty]
		return toIngredients(rxhandle, doQ(rxhandle, "SELECT rxcui1 from rxnrel where rxcui2=? and rela=?", (rxcui, val[0])), val[1])
	
	logging.warn('TTY "{}" is not mapped, skipping ingredient lookup'.format(tty))
	return []


def initVA(rxhandle):
	# SELECT DISTINCT tty, COUNT(tty) FROM rxnsat LEFT JOIN rxnconso AS r USING (rxcui) WHERE atn = "VA_CLASS_NAME" GROUP BY tty;
	rxhandle.execute('DROP TABLE IF EXISTS va_cache')
	rxhandle.execute('''CREATE TABLE va_cache
						(rxcui varchar UNIQUE, va text, level int)''')
	rxhandle.execute('''INSERT OR IGNORE INTO va_cache
						SELECT rxcui, atv, 0 FROM rxnsat
						WHERE atn = "VA_CLASS_NAME"''')
	rxhandle.sqlite.commit()

def traverseVA(rxhandle, rounds=3, expect=203175):
	""" Drug classes are set for a couple of different TTYs, it seems however
	most consistently to be defined on CD, SCD and AB TTYs.
	We cache the classes in va_cache and loop over rxcuis with known classes,
	applying the known classes to certain relationships.
	"""
	print("->  Starting VA class mapping")
	
	mapping = {
		'CD': [
			'has_tradename',			# > BD, SDB, ...
			'contained_in',				# > BPCK
			'consists_of',				# > SCDC
			'quantified_form',			# > SBD
		],
		'GPCK': [
			'has_tradename',			# > BPCK
		],
		
		'SBD': [
			'isa',						# > SBDG
			'has_ingredient',			# > BN
			'tradename_of',				# > SCD
			'consists_of',				# > SBDC
		],
		'SBDF': [
			'tradename_of',				# > SCDF
			'has_ingredient',
		],
		'SBDG': [
			'has_ingredient',			# > BN
			'tradename_of',				# > SCDG
		],
		
		'SCD': [
			'isa',						# > SCDF
			'has_quantified_form',		# > SCD
			'contained_in',				# > GPCK
			'has_tradename',			# > SBD
		],
		'SCDC': [
			'constitutes',				# > SCD
			'has_tradename',			# > SBDC
		],
		'SCDF': [
			'inverse_isa',				# > SCD
		],
		'SCDG': [
			'tradename_of',				# > SBDG
		]
	}
	
	found = set()
	ex_sql = 'SELECT rxcui, va FROM va_cache WHERE level = ?'
	
	for l in range(0,rounds):
		i = 0
		existing = rxhandle.fetchAll(ex_sql, (l,))
		num_drugs = len(existing)
		
		# loop all rxcuis that already have a class and walk their relationships
		for rxcui, va_imp in existing:
			found.add(rxcui)
			vas = va_imp.split('|')
			walkVAs(rxhandle, rxcui, vas, mapping, l)
			
			# progress report
			i += 1
			print('->  {}  {:.0%}'.format(l+1, i / num_drugs), end="\r")
		
		# commit after every round
		rxhandle.sqlite.commit()
		print('=>  {}  Found classes for {} of {} drugs ({:.1%})'.format(l+1, len(found), expect, len(found) / expect))
	
	print('->  VA class mapping complete')

def walkVAs(rxhandle, rxcui, vas, mapping, at_level=0):
	assert rxcui
	assert len(vas) > 0
	
	# get all possible relas for the given rxcui
	ttys = rxhandle.lookup_tty(rxcui)
	relas = set()
	for tty in ttys:
		if tty in mapping:
			relas.update(mapping[tty])
	
	# get all related rxcuis with the possible "rela" value(s)
	rel_fmt = ', '.join(['?' for r in relas])
	rel_sql = '''SELECT DISTINCT rxcui1 FROM rxnrel
				 WHERE rxcui2 = ? AND rela IN ({})'''.format(rel_fmt)
	rel_params = [rxcui]
	rel_params.extend(relas)
	
	exist_sql = 'SELECT va FROM va_cache WHERE rxcui = ?'
	
	for rel_rxcui in doQ(rxhandle, rel_sql, rel_params):
		storeVAs(rxhandle, rel_rxcui, vas, at_level+1)

def storeVAs(rxhandle, rxcui, vas, level=0):
	assert rxcui
	assert len(vas) > 0
	ins_sql = 'INSERT OR REPLACE INTO va_cache (rxcui, va, level) VALUES (?, ?, ?)'
	ins_val = '|'.join(vas)
	rxhandle.execute(ins_sql, (rxcui, ins_val, level))

def toDrugClasses(rxhandle, rxcui):
	sql = 'SELECT va FROM va_cache WHERE rxcui = ?'
	res = rxhandle.fetchOne(sql, (rxcui,))
	return res[0].split('|') if res is not None else []


def runImport(cb_host='localhost', cb_port=8091, cb_bucket='rxnorm'):
	
	# install keyboard interrupt handler
	def signal_handler(signal, frame):
		print("\nx>  Aborted")
		sys.exit(0)
	signal.signal(signal.SIGINT, signal_handler)
	
	# prepare databases
	RxNorm.check_database()
	rxhandle = RxNormLookup()
	rxhandle.prepare_to_cache_classes()
	
	# prepare Couchbase
	try:
		cb = couchbase.Couchbase.connect(
			host=cb_host,
			port=cb_port,
			bucket=cb_bucket
		)
	except Exception as e:
		logging.error(e)
		sys.exit(1)
	
	fmt = couchbase.FMT_JSON
	
	# fetch rxcui's of certain TTYs
	drug_types = ('SCD', 'SCDC', 'SBDG', 'SBD', 'SBDC', 'BN', 'SBDF', 'SCDG', 'SCDF', 'IN', 'MIN', 'PIN', 'BPCK', 'GPCK')
	param = ', '.join(['?' for d in drug_types])
	all_sql = "SELECT RXCUI, TTY from RXNCONSO where SAB='RXNORM' and TTY in ({})".format(param)
	
	all_drugs = rxhandle.fetchAll(all_sql, drug_types)
	num_drugs = len(all_drugs)
	
	# traverse VA classes
	if not rxhandle.can_cache():
		initVA(rxhandle)
		traverseVA(rxhandle, rounds=5, expect=num_drugs)
	
	# loop all
	i = 0
	w_ti = 0
	w_va = 0
	w_either = 0
	last_report = datetime.now()
	print('->  Indexing {} items'.format(num_drugs))
	
	for res in all_drugs:
		params = [res[0]]
		params.extend(drug_types)
		label = rxhandle.lookup_rxcui_name(res[0])
		
		# find ingredients (slow!) and drug classes (cached) and count
		ingr = toIngredients(rxhandle, [res[0]], res[1])
		ti = toTreatmentIntents(rxhandle, ingr, 'IN')
		va = toDrugClasses(rxhandle, res[0])
		if len(ti) > 0:
			w_ti += 1
		if len(va) > 0:
			w_va += 1
		if len(ti) > 0 or len(va) > 0:
			w_either += 1
		
		# create JSON document and insert
		d = {
			'_id': res[0],
			'tty': res[1],
			'label': label,
			'ingredients': list(ingr),
			'generics': list(toBrandAndGeneric(rxhandle, [res[0]], res[1])),
		#	'components': list(toComponents(rxhandle, [res[0]], res[1])),			# very slow
		#   'mechanisms': list(toMechanism(rxhandle, ingr, 'IN')),
			'treatmentIntents': list(ti),
			'va_classes': list(va)
		}
		
		# insert into Couchbase (using .set() will overwrite existing documents)
		# print(json.dumps(d, sort_keys=True, indent=2))
		cb.set(res[0], d, format=fmt)
		i += 1
		
		# inform every 5 seconds or so
		if (datetime.now() - last_report).seconds > 5:
			last_report = datetime.now()
			print('->  {:.1%}   n: {}, ti: {}, va: {}, either: {}'.format(i / num_drugs, i, w_ti, w_va, w_either), end="\r")
	
	print('->  {:.1%}   n: {}, ti: {}, va: {}, either: {}'.format(i / num_drugs, i, w_ti, w_va, w_either))
	print('=>  Done')


if '__main__' == __name__:
	logging.basicConfig(level=logging.INFO)
	runImport()
