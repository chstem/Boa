# -*- coding: utf-8 -*-

# a collection of functions to filter and correct markdown and tex commands

from __future__ import unicode_literals
import re
import string

def check_balanced_delimiters(markdown, delims='{[('):
    """check if all curly braces "{}", brackets "[]" and parenthesis "()" are closed"""

    if '{' in delims:
        braces_open = len(re.findall(r'(?<!\\){', markdown))
        braces_close = len(re.findall(r'(?<!\\)}', markdown))
        braces = braces_open - braces_close
    else:
        braces = 0

    if '[' in delims:
        brackets_open = len(re.findall(r'(?<!\\)\[', markdown))
        brackets_close = len(re.findall(r'(?<!\\)\]', markdown))
        brackets = brackets_open - brackets_close
    else:
        brackets = 0

    if '(' in delims:
        parenthesis_open = len(re.findall(r'(?<!\\)\(', markdown))
        parenthesis_close = len(re.findall(r'(?<!\\)\)', markdown))
        parenthesis = parenthesis_open - parenthesis_close
    else:
        parenthesis = 0

    if braces == brackets == parenthesis == 0:
        return 0
    else:
        return {'braces':braces,'brackets':brackets,'parenthesis':parenthesis}

def ensure_mathmode(markdown):
    """ensure math mode commands are wrapped in $$"""

    mathcommands = (
        '\\alpha', '\\beta', '\\gamma', '\\delta', '\\epsilon',
        '\\varepsilon', '\\zeta', '\\eta', '\\theta', '\\vartheta',
        '\\iota', '\\kappa', '\\lambda', '\\mu', '\\nu', '\\xi',
        '\\pi', '\\varpi', '\\rho', '\\varrho', '\\sigma',
        '\\varsigma', '\\tau', '\\upsilon', '\\phi', '\\varphi',
        '\\chi', '\\psi', '\\omega', '\\Gamma', '\\Delta', '\\Theta',
        '\\Lambda', '\\Xi', '\\Pi', '\\Sigma', '\\Upsilon', '\\Phi',
        '\\Psi', '\\Omega',
        '\\ge', '\\le', '\\leq', '\\geq', '\\times', '\\pm', '\\mp', '\\div', '\\circ',
        '\\equiv', '\\neq', '\\propto', '\\sim', '\\approx',
        '\\rightarrow', '\\leftarrow', '\\Rightarrow', '\\Leftarrow',
        '\\ce',
        )

    mathenvironments = [
        'equation', 'align', 'eqnarray', 'math', 'displaymath',
        'multline', 'gather', 'flalign', 'alignat',
        ]
    # add starred versions
    mathenvironments += [cmd+'*' for cmd in mathenvironments]

    def ismath_mode():
        return math_inline or math_env or math_ddollar

    def ismath_macro(macro):
        i = macro.find('{')
        if i == -1:
            i = None
        return macro[:i] in mathcommands

    math_inline = 0
    math_env = 0
    math_ddollar = False # $$ $$
    macro = ''
    macro_env = ''
    data_new = ''
    state = 'normal'
    prev_char = ''
    brakets = 0

    for char in markdown:

        # check if char triggers change of state
        if state == 'normal':
            if char == '\\':
                # macro start
                state = 'macro'
                macro = char
                prev_char = char
                continue

        elif state == 'macro':
            if char == '{':
                brakets += 1
                macro += char
                continue
            if char == '{':
                brakets -= 1
                macro += char
                if brakets != 0:
                    continue

            if char in string.whitespace+'[-\\$':
                # macro end
                if macro == '\\begin':
                    state = 'env_begin'
                if macro == '\\end':
                    state = 'env_end'

                # append macro
                if not ismath_mode() and ismath_macro(macro):
                    # preceding math mode ?
                    data_p = data_new.rstrip(' ')
                    if data_p[-1] == '$' and data_p[-2] != '$':
                        data_new = data_p[:-1]
                        data_new += macro + '$'
                    else:
                        data_new += '$%s$' %macro
                else:
                    data_new += macro

                # reset macro
                if char == '\\':
                    macro = char
                    prev_char = char
                    continue
                else:
                    macro = ''
                    if not state.startswith('env'):
                        state = 'normal'

        elif state.startswith('env'):
            if char == '}':
                # env end
                if macro_env[1:] in mathenvironments:
                    if state == 'env_begin':
                        math_env += 1
                    elif state == 'env_end':
                        math_env -= 1

                # append env
                data_new += macro_env
                macro_env = ''
                state = 'normal'

        if char == '$':
            if math_env:
                # escape in math environments
                if prev_char != '\\':
                    data_new += '\\'
            else:
                if prev_char == '$':
                    # $$ $$
                    math_ddollar = not math_ddollar
                # math_inline start/end
                math_inline = not math_inline

        # append char
        if state == 'macro':
            macro += char
        elif state.startswith('env'):
            macro_env += char
        elif state == 'normal':
            data_new += char

        prev_char = char

    return data_new

def filter_figures(markdown):
    """removes linked figures"""
    return re.sub('!\[.*?\]\(.*?\)', '', markdown)
