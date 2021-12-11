from pycparser.ply.lex import LexToken
import pytest
from transform.snippet import SnippetLexer

@pytest.fixture()
def lexer():
    return SnippetLexer()

def test_snippet_lexer_new(lexer: SnippetLexer):
    assert lexer.errors == []
    assert lexer.status == 'pending'

def test_snippet_lexer_no_valid_toks(lexer: SnippetLexer):
    toks, status = lexer.lex('\\')
    assert toks == []
    assert status == 'error'

    toks, status = lexer.lex('\n')
    assert toks == []
    assert status == 'success' # TODO: should this be error?

def test_snippet_lexer_success_simple(lexer: SnippetLexer):
    toks, status = lexer.lex('2 + 3')
    print(toks)
    assert len(toks) == 3
    for tok in toks:
        assert isinstance(tok, LexToken)


    assert toks[0].type == 'INT_CONST_DEC'
    assert toks[0].value == '2'
    assert toks[1].type == 'PLUS'
    assert toks[1].value == '+'
    assert toks[2].type == 'INT_CONST_DEC'
    assert toks[2].value == '3'

    assert status == 'success'

def test_snippet_lexer_unbalanced_lbrace(lexer: SnippetLexer):
    toks, status = lexer.lex('int main() {')
    assert len(toks) == 5
    assert status == 'error'
    assert len(lexer.errors) == 1
    assert lexer.errors[0] == 'Unbalanced braces'

def test_snippet_lexer_unbalanced_rbrace(lexer: SnippetLexer):
    toks, status = lexer.lex('int main() }')
    assert len(toks) == 5
    assert status == 'error'
    assert len(lexer.errors) == 1
    assert lexer.errors[0] == 'Unbalanced braces'