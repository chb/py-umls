#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#	Run this script to perform the RxNorm linking process and store the
#	documents in a NoSQL server.

import os
import sys
import logging

import pymongo
#import couchbase

from rxnorm_link import runImport


class DocHandler(object):
	""" Superclass for simple database import.
	"""
	
	def __init__(self):
		self.documents = []
	
	def addDocument(self, doc):
		if doc is not None:
			self.documents.append(doc)
	
	def finalize(self):
		pass


class MongoDocHandler(DocHandler):
	""" Handles documents for storage in MongoDB.
	"""
	
	def __init__(self):
		super().__init__()
		db_host = os.environ.get('MONGO_HOST')
		db_host = db_host if db_host else 'localhost'
		db_port = int(os.environ.get('MONGO_PORT'))
		db_port = db_port if db_port else 27017
		db_name = os.environ.get('MONGO_DB')
		db_name = db_name if db_name else 'default'
		db_bucket = os.environ.get('MONGO_BUCKET')
		db_bucket = db_bucket if db_bucket else 'rxnorm'
		
		conn = pymongo.MongoClient(host=db_host, port=db_port)
		db = conn[db_name]
		
		# authenticate
		db_user = os.environ.get('MONGO_USER')
		db_pass = os.environ.get('MONGO_PASS')
		if db_user and db_pass:
			db.authenticate(db_user, db_pass)
		
		self.mng = db[db_bucket]
		self.mng.ensure_index('ndc')
		self.mng.ensure_index('label')
	
	def addDocument(self, doc):
		super().addDocument(doc)
		if 0 == len(self.documents) % 50:
			self._insertAndClear()
	
	def finalize(self):
		self._insertAndClear()
	
	def _insertAndClear(self):
		if len(self.documents) > 0:
			self.mng.insert(self.documents)
			self.documents.clear()
	
	def __str__(self):
		return "MongoDB {}".format(self.mng)


class CSVHandler(DocHandler):
	""" Handles CSV export. """
	
	def __init__(self):
		super().__init__()
		self.csv_file = 'rxnorm.csv'
		self.csv_handle = open(self.csv_file, 'w')
		self.csv_handle.write("rxcui,tty,ndc,name,va_classes,treating,ingredients\n")
	
	def addDocument(self, doc):
		self.csv_handle.write('{},"{}",{},"{}","{}","{}","{}"{}'.format(
			doc.get('rxcui', '0'),
			doc.get('tty', ''),
			doc.get('ndc', ''),
			doc.get('label', ''),
			';'.join(doc.get('drugClasses') or []),
			';'.join(doc.get('treatmentIntents') or []),
			';'.join(doc.get('ingredients') or []),
			"\n"
		))
	
	def __str__(self):
		return 'CSV file "{}"'.format(self.csv_file)


if '__main__' == __name__:
	logging.basicConfig(level=logging.INFO)
	
	if 'did' != os.environ.get('DID_SOURCE_FOR_SETUP', 0):
		logging.error('You should use "rxnorm_link_run.sh" in order to run the linking process')
		sys.exit(1)
	
	# create handler and run
	ex_type = os.environ.get('EXPORT_TYPE')
	handler = None
	if ex_type is not None:
		try:
			if 'mongo' == ex_type:
				handler = MongoDocHandler()
			elif 'couch' == ex_type:
				raise Exception('Couchbase not implemented')
			elif 'csv' == ex_type:
				handler = CSVHandler()
			else:
				raise Exception('Unsupported type: {}'.format(ex_type))
		except Exception as e:
			logging.error(e)
			sys.exit(1)
	
	print('->  Processing to {}'.format(handler))
	runImport(doc_handler=handler)
