# -*- coding: utf-8 -*-

# a collection of functions to filter and correct tex code

from __future__ import unicode_literals
import re
import string

def remove_preamble(content):
    ''' remove preamble, \begin{document} and \end{document} if included '''

    # get last occurence of \begin{document}
    index = content.rfind('\\begin{document}')

    if not (index == -1):

        # remove \begin{document} and everything before
        content = content[index+len('\\begin{document}'):]

    # remove \end{document}
    content = content.replace('\\end{document}', '')

    return content

def check_balanced_delimiters(texcode, delims='{[('):

    ''' check if all curly braces "{}", brackets "[]" and parenthesis "()" are closed '''

    if '{' in delims:
        braces_open = len(re.findall(r'(?<!\\){', texcode))
        braces_close = len(re.findall(r'(?<!\\)}', texcode))
        braces = braces_open - braces_close
    else:
        braces = 0

    if '[' in delims:
        brackets_open = len(re.findall(r'(?<!\\)\[', texcode))
        brackets_close = len(re.findall(r'(?<!\\)\]', texcode))
        brackets = brackets_open - brackets_close
    else:
        brackets = 0

    if '(' in delims:
        parenthesis_open = len(re.findall(r'(?<!\\)\(', texcode))
        parenthesis_close = len(re.findall(r'(?<!\\)\)', texcode))
        parenthesis = parenthesis_open - parenthesis_close
    else:
        parenthesis = 0

    if braces == brackets == parenthesis == 0:
        return 0
    else:
        return {'braces':braces,'brackets':brackets,'parenthesis':parenthesis}

def escape_symbols(texcode, symbols='%&#'):

    ''' escape special characters '''

    def escape_symbol(matchobj):
        return matchobj.string[matchobj.start()]+'\\'+ matchobj.string[matchobj.end()-1]

    for symbol in symbols:
        texcode = re.sub(r'[^\\\\]'+symbol, escape_symbol, texcode)

    return texcode

def ensure_mathmode(texcode):

    ''' ensure math mode commands are wrapped in $$ '''

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
        )

    mathenvironments = [
        'equation', 'align', 'eqnarray', 'math', 'displaymath',
        'multline', 'gather', 'flalign', 'alignat',
        ]
    # add starred versions
    mathenvironments += [cmd+'*' for cmd in mathenvironments]

    def ismathmode():
        return math_inline or math_env

    math_inline = 0
    math_env = 0
    macro = ''
    macro_env = ''
    data_new = ''
    state = 'normal'
    prev_char = ''

    for char in texcode:

        # check if char triggers change of state
        if state == 'normal':
            if char == '\\':
                # macro start
                state = 'macro'
                macro = char
                prev_char = char
                continue

        elif state == 'macro':
            if char in string.whitespace+'{[-\\$':
                # macro end
                if macro == '\\begin':
                    state = 'env_begin'
                if macro == '\\end':
                    state = 'env_end'

                # append macro
                if not ismathmode() and (macro in mathcommands):
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
                print(repr(prev_char), ord(prev_char))
                if prev_char != '\\':
                    data_new += '\\'
            else:
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

    # remove double $
    data_new = data_new.replace('$$', '')

    return data_new

def switch_footnote(texcode):

    ''' move \\footnote if after \\footnotemark '''

    # check order of \footnotemark[?] and \footnote{}
    imark = -1
    while True:

        # get next imark
        try:
            imark = texcode.index('\\footnotemark[', imark+1)
        except ValueError:
            break

        # find all occurences of \footnote
        footnote_indices = [m.start() for m in re.finditer(r'\\footnote\{', texcode)]

        # get n (\footnotemark[n])
        imark_end = texcode.index(']', imark)
        try:
            nmark = int(texcode[imark+14:imark_end])
        except ValueError:
            continue

        # get footnote corresponding to footnotemark
        try:
            inote = footnote_indices[nmark-1]
        except IndexError:
            # footnotemark to large
            continue

        # check if at least n \footnote{} before
        if inote > imark:

            # get end of \footnote{}
            curly = 0
            for ichar, char in enumerate(texcode[inote+9:]):
                if char == '{':
                    curly += 1
                elif char == '}':
                    curly -= 1
                if not curly:
                    inote_end = ichar+inote+9
                    break

            # exchange \footnotemark[] and corresponding footnote{}
            mark, note = texcode[imark:imark_end+1], texcode[inote:inote_end+1]
            texcode = texcode[:imark] + note + texcode[imark_end+1:inote] + mark + texcode[inote_end+1:]

    # check for \footnotemark[] on a single line
    imark = 0
    while True:

        # get imark
        try:
            imark = texcode.index('\n\\footnotemark[', imark)
            imark_end = texcode.index(']', imark)
        except ValueError:
            break

        # delete \footnotemark[]
        texcode = texcode[:imark] + texcode[imark_end+1:]

    return texcode

def replace_doublefootnote(texcode):

    ''' replace multiple occurences of the same \\footnote{} with \\footnotemark[] '''

    inote = 0
    footnote_counter = 0
    while True:

        # get inote
        try:
            inote = texcode.index('\\footnote{', inote+1)
            footnote_counter += 1
        except ValueError:
            break

        # get end of \footnote{}
        curly = 0
        for ichar, char in enumerate(texcode[inote+9:]):
            if char == '{':
                curly += 1
            elif char == '}':
                curly -= 1
            if not curly:
                inote_end = ichar+inote+9
                break
        footnote = texcode[inote:inote_end+1]

        # check for repetitions
        inote2 = inote_end
        while True:

            try:
                inote2 = texcode.index(footnote, inote2+1)
                inote2_end = inote2 + inote_end - inote
            except ValueError:
                break

            # replace by \footnotemark[]
            texcode = texcode[:inote2] + '\\footnotemark[%i]' %footnote_counter + texcode[inote2_end+1:]

    return texcode

def set_linebreaks(texcode):

    ''' make sure every line ends with a linebreak '''

    texcode = texcode.replace(r'\newline', r'\\')
    texcode = re.sub('(?<!\\\\\\\\)\n', '\\\\\\\n', texcode)

    # revert \\ after \placefigure(*)
    texcode =  re.sub(r'(\\placefigure\*?)(\\\\)+', r'\1', texcode)

    return texcode
