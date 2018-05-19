# -*- coding: utf-8 -*-

# wrapper for pandoc: convert various markup formats
from __future__ import unicode_literals
from subprocess import Popen, PIPE

markdown_reader = 'markdown'

def latex2html(latex):
    pandoc = Popen(
        ['pandoc', '--from=latex', '--to=html', '--mathml'],
        stdin=PIPE, stdout=PIPE
    )
    out, err = pandoc.communicate(latex.encode('utf-8'))
    out = out.decode('utf-8').rstrip('\n')
    return out

def markdown2html(markdown):
    pandoc = Popen(
        ['pandoc', '--from='+markdown_reader, '--to=html', '--mathml'],
        stdin=PIPE, stdout=PIPE
    )
    out, err = pandoc.communicate(markdown.encode('utf-8'))
    out = out.decode('utf-8').rstrip('\n')
    return out

def markdown2latex(markdown):
    pandoc = Popen(
        ['pandoc', '--from='+markdown_reader+'-auto_identifiers', '--to=latex'],
        stdin=PIPE, stdout=PIPE
    )
    out, err = pandoc.communicate(markdown.encode('utf-8'))
    out = out.decode('utf-8').rstrip('\n')
    return out
