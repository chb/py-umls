#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#	Graphable objects for fun
#
#	2014-02-18	Created by Pascal Pfiffner

import os
import uuid
import subprocess
import tempfile


class GraphableObject (object):
	_name = None		# The name uniquely identifying the object
	label = None		# The label to show in place of the name
	shape = None
	style = None
	color = None
	announced_via = None
	
	def __init__(self, name, label=None):
		self._name = name if name else 'o' + uuid.uuid4().hex
		self.label = label
	
	@property
	def name(self):
		return self._name if self._name else 'unnamed'
	
	def inner_dot(self):
		if self.label or self.style or self.color or self.shape:
			inner = []
			if self.shape:
				inner.append("shape={}".format(self.shape))
			if self.style:
				inner.append("style={}".format(self.style))
			if self.color:
				inner.append("color={}".format(self.color))
			if self.label:
				inner.append('label="{}"'.format(self.label))
			return "[{}]".format(','.join(inner))
		return None
	
	def dot_representation(self):
		inner = self.inner_dot()
		if inner:
			return "\t{} {};\n".format(self.name, inner)
		return "\t{};\n".format(self.name)
	
	def announce_to(self, dot_context, via=None):
		""" Announce the receiver to the context.
		Subclasses MUST NOT announce other graphable objects they are holding
		on to here but they MUST announce them in "deliver_to" if appropriate.
		- dot_context The context to announce to
		- via If not-None the other GraphableObject that is responsible for
		  announcing the receiver
		"""
		self.announced_via = via
		dot_context.announce(self)
	
	def deliver_to(self, dot_context, is_leaf):
		""" Call the context's "deliver" method.
		This method is guaranteed to only be called once per context. Hence
		subclasses that hold on to other graphable objects MUST ANNOUNCE those
		instances here (but NOT deliver them) but ONLY IF "is_leaf" is not True.
		- dot_context The context to deliver to
		- is_leaf If True means the receiver is intended to be a leaf object
		"""
		dot_context.deliver(self)


class GraphableRelation (GraphableObject):
	relation_from = None			# first GraphableObject instance
	relation_to = None				# second GraphableObject instance
	
	def __init__(self, rel_from, label, rel_to):
		name = "{}->{}".format(rel_from.name, rel_to.name)
		super().__init__(name, label)
		self.relation_from = rel_from
		self.relation_to = rel_to
	
	def dot_representation(self):
		if self.relation_to:
			return "\t{} -> {} {};\n".format(
				self.relation_from.name,
				self.relation_to.name,
				self.inner_dot() or ''
			)
		return ''
	
	def deliver_to(self, dot_context, is_leaf):
		self.relation_from.announce_to(dot_context, self)
		self.relation_to.announce_to(dot_context, self)
		super().deliver_to(dot_context, is_leaf)		# deliver after announcing our nodes!


class DotContext (object):
	items = None
	source = None
	depth = 0
	max_depth = 8		# there is something fishy still, make this double the tree depth you want
	
	def __init__(self, max_depth=None):
		self.items = set()
		self.source = ''
		self.depth = 0
		if max_depth is not None:
			self.max_depth = max_depth
	
	def announce(self, obj):
		if obj.name not in self.items:
			self.items.add(obj.name)
			
			self.depth += 1
			obj.deliver_to(self, self.depth > self.max_depth)
			self.depth -= 1
	
	def deliver(self, obj):
		self.source += obj.dot_representation()
	
	def get(self):
		return self.source


class GraphvizGraphic (object):
	cmd = 'dot'
	out_type = 'png'
	out_file = None
	
	def __init__(self, outfile):
		self.out_file = outfile
	
	def executableCommand(self, infile):
		return [
			self.cmd,
			'-T{}'.format(self.out_type),
			infile,
			'-o', format(self.out_file),
		]
	
	def write_dot_graph(self, obj):
		assert self.out_file
		
		context = DotContext()
		obj.announce_to(context)
		dot = context.get()
		
		source = """digraph G {{
	ranksep=equally;\n{}}}\n""".format(dot)
		
		# write to a temporary file
		filedesc, tmpname = tempfile.mkstemp()
		with os.fdopen(filedesc, 'w') as handle:
			handle.write(source)
		
		# execute dot	
		cmd = self.executableCommand(tmpname)
		ret = subprocess.call(cmd)
		
		os.unlink(tmpname)
		if ret > 0:
			raise Exception('Failed executing: "{}"'.format(cmd))
		
		subprocess.call(['open', self.out_file])

