import pytest
from scrape.stack import StackOverflowScraper

@pytest.fixture()
def stack():
    return StackOverflowScraper(cache_path='.cache/stack_scraper_tests')

def test_scrape_stackoverflow_page(stack: StackOverflowScraper):
    assert type(stack) is StackOverflowScraper
    # Test that the scraper works
    test_data = stack.scrape_page('https://stackoverflow.com/questions/69729326/endless-sine-generation-in-c')

    assert type(test_data) is list
    assert len(test_data) > 0

    for answer in test_data:
        assert type(answer) is dict
        # assert answer['question_id'] == 69729326 # This is the question we're scraping
        assert 'snippets' in answer
        assert type(answer['snippets']) is str

        assert 'score' in answer
        assert type(answer['score']) is int

        assert 'answer_id' in answer
        assert type(answer['answer_id']) is int

        assert 'page_pos' in answer
        assert type(answer['page_pos']) is int

        assert 'is_highest_scored' in answer
        assert type(answer['is_highest_scored']) is bool

        assert 'question_has_highest_accepted_answer' in answer
        assert type(answer['question_has_highest_accepted_answer']) is bool

        assert 'is_accepted' in answer
        assert type(answer['is_accepted']) is bool
        assert 'source' in answer
        assert type(answer['source']) is str

        assert 'author_id' in answer
        assert type(answer['author_id']) is int

        assert 'author_username' in answer
        assert type(answer['author_username']) is str

    print(test_data[0]['snippets'])