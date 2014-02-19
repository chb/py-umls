#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#	Draw an RxNorm graph for a given RxCUI or RxAUI.
#	You must have "dot" installed (Graphviz)
#
#	2014-02-18	Created by Pascal Pfiffner

import sys

from rxnorm import RxNormAUI
from graphable import GraphvizGraphic


if '__main__' == __name__:
	rxaui = sys.argv[1] if 2 == len(sys.argv) else None
	if rxaui is None:
		print('x>  Provide a RXAUI as first argument')
		sys.exit(0)
	
	rx = RxNormAUI(rxaui)
	gv = GraphvizGraphic('graph.png')
	gv.write_dot_graph(rx)
