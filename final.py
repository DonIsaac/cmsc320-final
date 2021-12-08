# %%
from pymongo import MongoClient, UpdateOne # https://pymongo.readthedocs.io/en/stable/tutorial.html
import dns
import requests
import requests_cache # https://requests-cache.readthedocs.io/en/stable/
import datetime
from typing import List, Dict, Tuple, Optional
import json
import time
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
import random


load_dotenv()
None

# %%
# Connect to MongoDB
def get_mongo_client() -> MongoClient:
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        raise Exception('MONGO_URI not set')
    client = MongoClient(_mongo_uri, tls=True)
    return client
# _mongo_uri = 'mongodb+srv://admin:<password>@cmsc320-final-tutorial.i5dh9.mongodb.net/myFirstDatabase?retryWrites=true&w=majority'
# print(_mongo_uri)

client = get_mongo_client()
db = client['stackOverflowDB']
questions = db['questions']
answers = db['answers']

# %%
# Set up request caching for StackOverflow API
session = requests_cache.CachedSession('.cache/stack_cache', cache_control=True, stale_if_error=True, backend='filesystem')

# %% [markdown]
# # Getting StackOverflow Questions
# 
# Questions are procured from the [StackOverflow REST API](https://api.stackexchange.com/docs), specifically the [/questions endpoint](https://api.stackexchange.com/docs/questions#order=desc&sort=activity&tagged=c%3Bc%2B%2B&filter=default&site=stackoverflow). We'll be limiting our search to C/C++ code snippets for simplicity.

# %%
def get_stackoverflow_questions(**kwargs):
    """
    
    """
    
    pagesize: int = kwargs.get('pagesize', 100) # How many questions to return per page
    assert 1 <= pagesize <= 100                 # Stack allows [0, 100] but why waste API calls?

    page: int = kwargs.get('page', 1)           # Starting page index, 1-indexed
    assert page >= 1                       

    maxpages: int = kwargs.get('maxpages', 10)  # Max number of pages to return
    assert maxpages >= 1

    api_key: Optional[str] = kwargs.get('api_key')

    question_boundary_younger = datetime.datetime(2021, 12, 4) # No questions posted more recently than this will be returned
    done = False # Set to True if we hit our request quota or no more question data is available
    requests_made = 0

    # StackOverflow API query parameters common across all queries
    base_query_params: dict = {
        'site': 'stackoverflow',
        'sort': 'activity',
        'order': 'desc',
        'tagged': 'c',
        'pagesize': pagesize,
        'todate': int(question_boundary_younger.timestamp())
    }

    # Include the API key if one was provided
    if api_key:
        base_query_params['key'] = api_key

    while not done and requests_made < maxpages:
        query_params = base_query_params.copy()
        query_params['page'] = page

        # Returns a Common Wrapper Object
        # https://api.stackexchange.com/docs/wrapper
        r = session.get('https://api.stackexchange.com/2.3/questions', params=query_params)

        if r.status_code > 299:
            if r.headers['content-length'] == 0:
                r.raise_for_status()

            elif 'json' in r.headers['content-type']:
                error_json = r.json()
                raise requests.HTTPError(f'{r.status_code} {r.reason} API returned error {error_json["error_id"]}: {error_json["error_message"]}')
                
            else:
                raise requests.HTTPError(f'{r.status_code} {r.reason}: {r.text}')

                
        assert 'json' in r.headers['content-type'] # We're expecting JSON back

        requests_made += 1
        page += 1

        # Yield each question in the response
        body = r.json()
        assert 'items' in body
        assert isinstance(body['items'], list)
        yield body['items']

        # Check if we're done
        quota_remaining = body['quota_remaining']
        quota_max = body['quota_max']
        has_more: bool = body['has_more']
        done = not body['has_more'] or body['quota_remaining'] <= 0

        print('\r', f'Got {pagesize} questions from page #{page} (quota: {quota_remaining}/{quota_max})', end='')


        # Check if we need to back off before sending more requests. Only necessary if we're not done.
        backoff = body.get('backoff', 0)
        if not done and backoff > 0:
            print(f'Backoff requested, sleeping for {backoff} seconds')
            time.sleep(backoff)


# %%
# This takes a while, is expensive, and is only necessary once. This flag
# lets you skip this step if you've already run it.
should_scrape = True
drop = False
page_size = 100  # Number of questions to return per page
page = 185       # Starting page index, 1-indexed. Useful for continuing where you left off in the event of a crash

if should_scrape:

    if drop:
        print('Dropping questions collection')
        questions.drop()
        
    print('Scraping questions')
    # Scrape each page, bulk inserting each one into mongo
    for page in get_stackoverflow_questions(page=page, maxpages=100, pagesize=page_size):
        if type(page) is not list:
            assert type(page) is dict
            page = [page]

        page = filter(lambda q: q['answer_count'] > 0, page)
        upserts = [UpdateOne({'_id': q['question_id']}, {'$set': q}, upsert=True) for q in page]
        questions.bulk_write(upserts)
        time.sleep(0.5 + random.random() / 2) # Sleep for a bit to avoid hitting the API too hard


# %%
for j in range(1, 5):
    print('\r', f'Waiting: {j}', end='')
    time.sleep(1)

# %% [markdown]
# # Scraping StackOverflow Answers

# %%
def get_questions(**kwargs):
    pagesize = kwargs.get('pagesize', 100) # How many questions to return per page
    assert 1 <= pagesize 

    page = kwargs.get('page', 1)           # Starting page index, 1-indexed
    assert page >= 1

    # Calculate number of documents to skip
    skips = page_size * (page_num - 1)

    # Skip and limit
    cursor = questions.find().skip(skips).limit(page_size)
    for doc in cursor:
        yield doc

# %%
def scrape_stackoverflow_page(url: str) -> List[Dict]:

    # Load the page into BeautifulSoup
    r = session.get(url)
    html_doc = r.text
    soup = BeautifulSoup(html_doc, 'html.parser')

    answers = soup.select('.answer')

    answers_parsed = []
    for answer in answers:
        answer_cell = answer.select_one('.answercell')

        answer_id = int(answer['data-answerid'])

        # Get all code snippet elements for the answer, skipping if there are none
        snippet_elems = answer_cell.select('pre > code')
        if not len(snippet_elems):
            continue

        # Contains the user name and id of the answerer
        user_details = answer.select_one('.post-signature .user-details > a')

        # Extract the answer author's user id. Anonymous users have no user id
        if user_details is None:
            user_id = None
            user_name = 'anonymous'
        else:
            _, _, user_id, user_name = user_details['href'].split('/') # takes form /users/:id/:name
            user_id = int(user_id) # May be -1 if posted by 'community'

        answer_data = {
            # 'question_id': question_id,
            'snippets': '\n'.join([code_block.text for code_block in snippet_elems]),
            'score': int(answer['data-score']),
            'answer_id': answer_id,
            'page_pos': int(answer['data-position-on-page']),
            'is_highest_scored': answer['data-highest-scored'] == '1',
            'question_has_highest_accepted_answer': answer['data-question-has-accepted-highest-score'] == '1',
            # 'is_accepted': answer.has_class('accepted-answer'),
            'is_accepted': 'accepted-answer' in answer['class'],
            # 'source': answer.select_one('a.js-share-link').get('href').strip(),
            'source': f'https://stackoverflow.com/a/{answer_id}',
            'author_id': user_id,
            'author_username': user_name,
        }

        answers_parsed.append(answer_data)

    return answers_parsed

# Test that the scraper works
test_data = scrape_stackoverflow_page('https://stackoverflow.com/questions/69729326/endless-sine-generation-in-c')

assert type(test_data) is list
assert len(test_data) > 0

for answer in test_data:
    assert type(answer) is dict
    # assert answer['question_id'] == 69729326 # This is the question we're scraping
    assert 'snippets' in answer
    assert 'score' in answer
    assert 'answer_id' in answer
    assert 'page_pos' in answer
    assert 'is_highest_scored' in answer
    assert 'question_has_highest_accepted_answer' in answer
    assert 'is_accepted' in answer
    assert 'source' in answer
    assert 'author_id' in answer
    assert 'author_username' in answer

print(test_data[0]['snippets'])

# %%
drop = False         # Set to True to drop the collection before scraping
page_size = 100      # The number of questions to scrape in each page
start_page = 170     # The page to start scraping at, allows for resuming scraping after a crash
should_scrape = True # Set to True to scrape the questions collection
num_pages = int(questions.count_documents({}) / page_size)

if should_scrape:

    # Drop the collection if we're dropping it
    if drop:
        print('Dropping answers collection') 
        answers.drop()

    # Scrape each page of questions, bulk inserting answers into mongo
    assert start_page > 0
    for page_num in range(start_page, num_pages + 1):
        # page_num = i + 1
        print(f'Scraping page {page_num}/{num_pages} ', end = '')

        for question in get_questions(page=page_num, pagesize=page_size):

            # Get the answers for this question, skipping if no relevant answers are available
            answers_data = scrape_stackoverflow_page(question['link'])
            if not len(answers_data):
                print('x', end = '')
                continue

            # Add the question id to each answer
            for answer_data in answers_data:
                answer_data['question_id'] = question['question_id']

            # Bulk insert the answers
            upserts = [UpdateOne({'_id': answer['answer_id']}, {'$set': answer}, upsert=True) for answer in answers_data]
            answers.bulk_write(upserts)
            print('.', end = '')
            time.sleep(0.60 + random.random()) # Don't spam the server, otherwise CloudFlare will complain

        print('')

# %%



