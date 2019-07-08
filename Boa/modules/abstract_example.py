# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from codecs import open
from os.path import join, dirname, realpath
from .database import *

filename = join(dirname(realpath(__file__)), '../preferences/abstract_example.py')
with open(filename, encoding='utf-8') as fd:
    code = compile(fd.read(), filename, 'exec')
    exec(code, globals(), locals())
