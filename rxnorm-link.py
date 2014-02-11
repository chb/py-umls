#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#	Precompute and store interesting RXCUI relationships
#
#	2012-09-28	Created by Josh Mandel
#	2014-02-10	Stolen by Pascal Pfiffner
#
#	For profiling: pycallgraph graphviz -- rxnorm-link.py

import json
import logging

from rxnorm import RxNorm, RxNormLookup


rxhandle = None

def doQ(q, p):
	return [x[0] for x in rxhandle.fetchAll(q, p)]

def toBrandAndGeneric(rxcuis, tty):
	ret = set()
	for rxcui in rxcuis:
		ret.update(doQ("SELECT rxcui1 from rxnrel where rxcui2=? and rela='tradename_of'", (rxcui,)))
	return ret

def toComponents(rxcuis, tty):
	ret = set()

	if tty not in ("SBD", "SCD"):
		return ret

	for rxcui in rxcuis:
		cs = doQ("SELECT rxcui1 from rxnrel where rxcui2=? and rela='consists_of'", (rxcui,))
		for c in cs:
			ret.update(doQ("SELECT rxcui from rxnconso where rxcui=? and sab='RXNORM' and tty='SCDC'", (c,)))        

	return ret

def toTreatmentIntents(rxcuis, tty):
	ret = set()
	for rxcui in rxcuis:
		ret.update(toTreatmentIntents_helper(rxcui, tty))
	return ret

def toTreatmentIntents_helper(rxcui, tty):
	assert tty=='IN'
	ret = []
	rxauis = doQ("SELECT rxaui from rxnconso where rxcui=? and tty='FN' and sab='NDFRT'", (rxcui,))
	for a in rxauis:
		a1 = doQ("SELECT rxaui1 from rxnrel where rxaui2=? and rela='may_treat'", (a,))
		if len(a1) > 0:
			dz = doQ("SELECT str from rxnconso where rxaui=? and tty='FN' and sab='NDFRT'", (a1[0],))
			dz = map(lambda x: x.replace(" [Disease/Finding]", ""), dz)
			ret.extend(dz)
	return ret

def toMechanism(rxcuis, tty):
	ret = set()
	for v in rxcuis:
		ret.update(toMechanism_helper(v, tty))
	return ret

def toMechanism_helper(rxcui, tty):
	assert tty=='IN'
	ret = set()
	rxauis = doQ("SELECT rxaui from rxnconso where rxcui=? and tty='FN' and sab='NDFRT'", (rxcui,))
	for a in rxauis:
		a1 = doQ("SELECT rxaui1 from rxnrel where rxaui2=? and rela='has_mechanism_of_action'", (a,))
		if len(a1) > 0:
			moa = doQ("SELECT str from rxnconso where rxaui=? and tty='FN' and sab='NDFRT'", (a1[0],))
			moa = map(lambda x: x.replace(" [MoA]", ""), moa)
			ret.update(moa)
	return ret


def toIngredients(rxcuis, tty):
	ret = set()
	for v in rxcuis:
		ret.update(toIngredients_helper(v, tty))
	return ret

def toIngredients_helper(rxcui, tty):
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
		return doQ("SELECT rxcui1 from rxnrel where rxcui2=? and rela=?", (rxcui, map_direct[tty]))
	
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
		return toIngredients(doQ("SELECT rxcui1 from rxnrel where rxcui2=? and rela=?", (rxcui, val[0])), val[1])
	
	logging.warn('TTY "{}" is not mapped, skipping ingredient lookup'.format(tty))
	return []



if '__main__' == __name__:
	RxNorm.check_database()
	rxhandle = RxNormLookup()
	
	# prepare some SQL
#	drug_types = ('SCD', 'SCDC', 'SBDG', 'SBD', 'SBDC', 'BN', 'SBDF', 'SCDG', 'SCDF', 'IN', 'MIN', 'PIN', 'BPCK', 'GPCK')
	drug_types = ('SCD', 'SCDC', 'SBDG', 'SBD')
	param = ', '.join(['?' for x in range(0, len(drug_types))])
	sql = "SELECT RXCUI, TTY from RXNCONSO where SAB='RXNORM' and TTY in ({})".format(param)
	
	label_sql = "SELECT STR from RXNCONSO where RXCUI=? and SAB='RXNORM' and TTY in ({})".format(param)
	
	all_drugs = rxhandle.fetchAll(sql, drug_types)
	
	# clean old links
	# TODO: do clean indeed
	
	# loop results
	for res in all_drugs:
		ii = toIngredients([res[0]], res[1])
		
		params = [res[0]]
		params.extend(drug_types)
		label = rxhandle.execute(label_sql, params).fetchone()[0]
		
		# create JSON document and insert
		d = {
			'_id': res[0],
			'tty': res[1],
			'label': label,
			'ingredients': list(ii),
			'generics': list(toBrandAndGeneric([res[0]], res[1])),
			'components': list(toComponents([res[0]], res[1])),
		#   'mechanisms': list(toMechanism(ii, 'IN')),
			'treatmentIntents': list(toTreatmentIntents(ii, 'IN')),
			'va_class': rxhandle.find_va_drug_class(res[0])
		}
		print(json.dumps(d, sort_keys=True, indent=2))
		# TODO: insert
		
		# if int(res[0]) > 500:
		# 	break

