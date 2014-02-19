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
	_name = None
	label = None
	shape = None
	style = None
	color = None
	
	def __init__(self, name, label=None):
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
		print("delivering", self)
		dot_context.deliver(self)
	
	def announce_to(self, dot_context):
		""" Announce to the context if we need to declare properties.
		Subclasses MUST NOT announce other graphable objects they are holding
		on to here but they MUST announce them in their "deliver_to"
		implementation if they want them to be exported to the context.
		"""
		if self.should_announce():
			dot_context.announce(self)


class GraphableRelation (GraphableObject):
	relation_from = None			# first GraphableObject instance
	relation_to = None				# second GraphableObject instance
	
	def __init__(self, rel_from, label, rel_to):
		super().__init__(None, label)
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
	
	def deliver_to(self, dot_context):
		self.relation_from.announce_to(dot_context)
		self.relation_to.announce_to(dot_context)
		super().deliver_to(dot_context)


class DotContext (object):
	items = None
	source = None
	
	def __init__(self):
		self.items = set()
		self.source = ''
	
	def has(self, obj):
		return obj in self.items
	
	def announce(self, obj):
		if obj not in self.items:
			self.items.add(obj)
			obj.deliver_to(self)
	
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
	
	def command(self, infile):
		return [
			self.cmd,
			'-T{}'.format(self.out_type),
			'-o{}'.format(self.out_file),
			infile
		]
	
	def write_dot_graph(self, obj):
		assert self.out_file
		
		context = DotContext()
		obj.announce_to(context)
		dot = context.get()
		
		source = "digraph G {{\n{}}}\n".format(dot)
		print(source)
		# write to a temporary file
		filedesc, tmpname = tempfile.mkstemp()
		with os.fdopen(filedesc, 'w') as handle:
			handle.write(source)
			
			cmd = self.command(tmpname)
			ret = subprocess.call(cmd)
			print(cmd)
			print("ret", ret)
			#os.unlink(tmpname)
			if ret > 0:
				raise Exception('Failed executing: "{}"'.format(cmd))

