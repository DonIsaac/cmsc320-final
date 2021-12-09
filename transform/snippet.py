from typing import Dict, List, Tuple
from pycparser import CParser, c_lexer, parse_file
from pycparser.c_lexer import CLexer
import subprocess
import os

from pycparser.ply.lex import LexToken

# List of potential programs for parsing C/C++
# 'cc' is intentionally not included
_programs = ['gcc', 'g++', 'c++', 'clang', 'clang++']


class SnippetCleaner:
    def __init__(self, **kwargs):
        self.verbose: bool = kwargs.get('verbose', False)

        self.cc = self.cpp = CParser()

    def _init_parsers(self, cc_override=None, cpp_override=None):
        """
        TODO: Use this if pycparser doesn't come through
        """
        # Dict of all available C/C++ compiler programs.
        ccs = self._get_available_cc_progs()

        # Determine which C parser to use.
        if cc_override:
            assert cc_override in ccs
            self.cc = cc_override
        elif ccs['gcc']:
            self.cc = 'gcc'
        elif ccs['clang']:
            self.cc = 'clang'
        else:
            self.cc = CParser()

        # Determine which C++ parser to use.
        if cpp_override:
            assert cpp_override in ccs
            self.cpp = cpp_override
        elif ccs['g++']:
            self.cpp = 'g++'
        elif ccs['clang++']:
            self.cpp = 'clang++'
        elif ccs['c++']:
            self.cpp = 'c++'
        elif ccs['gcc']:  # Fallback to gcc (TODO: is this okay to do?)
            self.cpp = 'gcc'
        else:
            self.cc = CParser()

    def _get_available_cc_progs(self) -> Dict[str, bool]:
        """
        Checks for available C/C++ compiler programs.
        Returns a dictionary containing the names of the available C/C++ compiler, 
        and a boolean indicating if the compiler is available.
        """

        result: dict = {}
        for prog in _programs:
            try:
                completed_prog = subprocess.run(
                    [prog, '--version'], stdout=None, stderr=None)
                result[prog] = completed_prog.returncode == 0
            except:
                result[prog] = False

        return result

    def _check_c_snippet(self, snippet: str, name='') -> bool:
        """
        Checks if the code snippet is valid C code.
        TODO
        """
        if self.cc == 'gcc':
            status = subprocess.run(
                [self.cc, '-x', 'c', '-E', '-', '-o', '-'], stdout=None, stderr=None, input=snippet)
        try:
            self.parser.parse(snippet, name)
            return True
        except:
            return False

    # Parses a code snippet and checks if it is valid C code. If the check fails,
    # it checks if the snippet is valid C++ code. Returns a tuple containing
    # two booleans, the first one indicating if the code snippet is valid C code,
    # the second one indicating if the code snippet is valid C++ code.
    def parse(self, snippet: str, name: str = '') -> Tuple[bool, bool]:
        parser = CParser()
        try:
            parser.parse(snippet, name, 1 if self.verbose else 0)
            return (True, False)
        except:
            return (False, True)


class SnippetLexer:
    def __init__(self):
        self._lexer = CLexer(error_func=self._on_error, on_lbrace_func=self._on_lbrace,
                             on_rbrace_func=self._on_rbrace, type_lookup_func=self._type_lookup)
        # 'pending', 'running', 'error', 'success'
        self.status = 'pending'
        self.errors = []
        self.brace_depth = 0

    def lex(self, snippet: str) -> Tuple[List[LexToken], str]:
        """
        Lexes a code snippet and returns a tuple containing the lexed snippet and
        the lexer's status. The status can be 'pending', 'running', 'error', or 'success'.

        If the lexer's status is 'error', the errors list will contain a list of
        error messages.
        """
        
        self.reset()
        toks: List[LexToken] = []

        self.status = 'running'

        self._lexer.build()
        self._lexer.input(snippet)
        self._lexer.token()

        while True:
            tok = self._lexer.token()
            if not tok:
                break
            toks.append(tok)

        # Check for hanging open braces
        if self.brace_depth != 0:
            self.status = 'error'
            self.errors.append('Unbalanced braces')

        self.status = 'success' if self.status == 'running' else self.status
        return (toks, self.status)

    def reset(self):
        """
        Resets the lexer's internal state after lexing a snippet.
        """
        self.status = 'pending'
        self.errors = []
        self.brace_depth = 0


    def _type_lookup(self, token):
        return True

    def _on_lbrace(self):
        self.brace_depth += 1

    def _on_rbrace(self):
        self.brace_depth -= 1
        if self.brace_depth < 0:
            self.status = 'error'
            self.errors.append('Unbalanced braces')

    def _on_error(self, msg):
        self.status = 'error'
        self.errors.append(msg)
