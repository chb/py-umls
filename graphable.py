#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#	Graphable objects for fun
#
#	2014-02-18	Created by Pascal Pfiffner

import os
import subprocess
import tempfile


class GraphableObject (object):
	identifier = None
	_name = None
	label = None
	shape = None
	style = None
	color = None
	
	def __init__(self, identifier, name, label=None):
		self.identifier = identifier
		self._name = name
		self.label = label
	
	@property
	def name(self):
		return self._name if self._name else 'unnamed'
	
	def should_announce(self):
		if self.label or self.style or self.color or self.shape:
			return True
		return False
	
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
	
	def deliver_to(self, dot_context):
		""" Call the context's "deliver" method.
		This method is guaranteed to only be called once per context. Hence
		subclasses that hold on to other graphable objects MUST ANNOUNCE those
		instances here (but NOT deliver them).
		"""
		dot_context.deliver(self)
	
	def announce_to(self, dot_context):
		""" Announce to the context if we need to declare properties.
		Subclasses MUST NOT announce other graphable objects they are holding
		on to here but they MUST announce them in "announce_relations_to"
		if they want them to be exported to the context at one point.
		"""
		if self.should_announce():
			dot_context.announce(self)
	
	def announce_relations_to(self, dot_context):
		""" Announce any relations the receiver may have. This is called by the
		context if it desires the receiver's relations. """
		pass


class GraphableRelation (GraphableObject):
	relation_from = None			# first GraphableObject instance
	relation_to = None				# second GraphableObject instance
	
	def __init__(self, rel_from, label, rel_to):
		identifier = "{}->{}".format(rel_from.identifier, rel_to.identifier)
		super().__init__(identifier, None, label)
		self.relation_from = rel_from
		self.relation_to = rel_to
	
	def should_announce(self):
		return self.relation_from and self.relation_to
	
	def dot_representation(self):
		if self.relation_to:
			return "\t{} -> {} {};\n".format(
				self.relation_from.name,
				self.relation_to.name,
				self.inner_dot() or ''
			)
		
		return ''
	
	def announce_relations_to(self, dot_context):
		self.relation_from.announce_to(dot_context)
		self.relation_to.announce_to(dot_context)


class DotContext (object):
	items = None
	source = None
	depth = 0
	max_depth = 14
	
	def __init__(self, max_depth=None):
		self.items = set()
		self.source = ''
		self.depth = 0
		if max_depth is not None:
			self.max_depth = max_depth
	
	def announce(self, obj):
		if obj.identifier not in self.items:
			self.items.add(obj.identifier)
			
			obj.deliver_to(self)
			if self.depth < self.max_depth:
				self.depth += 1
				obj.announce_relations_to(self)
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
	ranksep=equally;
	{}}}\n""".format(dot)
		
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

