import requests
import requests_cache # https://requests-cache.readthedocs.io/en/stable/
import datetime
from typing import List, Dict, Tuple, Optional, Union
import json
import time
from bs4 import BeautifulSoup
import random

class StackOverflowScraper:
    def __init__(self, **kwargs):
        cache_path: Union[str, bool] = kwargs.get('cache_path', '.cache/stack_cache')
        if type(cache_path) is str:
            self.session = requests_cache.CachedSession(cache_path, cache_control=True, stale_if_error=True, backend='filesystem')
        else:
            self.session = requests.Session()
        
        # self.session = session

    def get_questions(self, **kwargs):
        """
        Gets recent questions from Stack Overflow using the Stack Overflow API.

        As this method is a generator, it will yield the questions as they are
        retrieved from the API in batches of `pagesize`. Each batch is called
        a page, and contains question objects as dicts.

        StackOverflow throttles the amount of requests that can be made to it
        based on the IP address of the client, or the API key of the applicaiton
        if one is provided. Providing a key is not necessary, but allows for
        more requests to be made each day.

        ## Keyword arguments:

        pagesize -- The number of questions to retrieve per API call. Must be 1<= `pagesize` <= 100. (default: 100) 
        page -- The page of questions to start at. Must be > 0. (default: 1)
        maxpages -- The maximum number of pages to retrieve. Must be > 0. (default: 10)
        api_key -- The Stack Overflow API key to use. (default: None)
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
            r = self.session.get('https://api.stackexchange.com/2.3/questions', params=query_params)

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

    def scrape_answers(self, url: str) -> List[Dict]:

        # Load the page into BeautifulSoup
        r = self.session.get(url)
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