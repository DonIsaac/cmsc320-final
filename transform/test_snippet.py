import os
from posix import listdir
from typing import Dict
import pytest
from clean.snippet import SnippetCleaner

@pytest.fixture(scope="function")
def snippet_cleaner():
    return SnippetCleaner(verbose=True)

@pytest.fixture
def test_cases():
    _test_cases = {
        'valid': {
            'c': [],
            'cpp': [],
        },
        'invalid': {
            'c': [],
            'cpp': [],
        },
    }

    this_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(this_dir, '__test__')

    for root, dirs, files in os.walk(test_dir):
        for file in files:
            # valid is either 'valid' or 'invalid'
            name, valid, ext = file.split('.')
            if not valid in _test_cases.keys():
                print(f'Skipping invalid test case file: {file}')
                continue

            test_case = {
                'name': os.path.abspath(os.path.join(root, file)),
                'content': open(os.path.join(root, file)).read()
            }

            # append the file name to the appropriate list list
            if ext in ['c', 'h']:
                _test_cases[valid]['c'].append(test_case)
            elif ext in ['cpp', 'hpp']:
                _test_cases[valid]['cpp'].append(test_case)
            else:
                raise Exception(f'Unknown file extension "{ext}" for test case {file}')

    return _test_cases


# @pytest.mark.usefixtures("snippet_cleaner", "test_cases")
def test_valid_c(snippet_cleaner: SnippetCleaner, test_cases):
    for test_case in test_cases['valid']['c']:
        print(test_case)
        # name, content = test_case
        # print(name)
        # print(content)
        is_valid_c, _ = snippet_cleaner.parse(test_case['content'], test_case['name'])
        assert is_valid_c