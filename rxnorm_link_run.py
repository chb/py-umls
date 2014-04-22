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


if '__main__' == __name__:
	logging.basicConfig(level=logging.INFO)
	
	if 'did' != os.environ.get('DID_SOURCE_FOR_SETUP', 0):
		print('x>  You should use "rxnorm_link_run.sh" in order to run the linking process')
		sys.exit(1)
	
	# create handler and run
	handler = None
	try:
		if os.environ.get('USE_MONGO', False):
			print('->  Using MongoDB')
			handler = MongoDocHandler()
		
		elif os.environ.get('USE_COUCH', False):
			raise Exception('Couchbase not implemented')
	
	except Exception as e:
		logging.error(e)
		sys.exit(1)
	
	print('->  Importing to {}'.format(handler))
	runImport(doc_handler=handler)
