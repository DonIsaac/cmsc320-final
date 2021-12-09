from bs4.element import ResultSet, Tag
from pymongo.database import Database
from pymongo import UpdateOne
import requests
import requests_cache # https://requests-cache.readthedocs.io/en/stable/
import datetime
from typing import Generator, List, Dict, Optional, Tuple, Union
import time
import random
from bs4 import BeautifulSoup

class StackOverflowScraper:
    """
    Scrapes StackOverflow for questions and answers.
    """

    def __init__(self, **kwargs):
        # May be a file path (str), a session object (CachedSession), False (no caching), or None (default)
        cache: Union[str, bool, requests_cache.CachedSession] = kwargs.get('cache', '.cache/stack_cache')

        if type(cache) is str:
            self.session = requests_cache.CachedSession(cache, cache_control=True, stale_if_error=True, backend='filesystem')
        elif type(cache) is requests_cache.CachedSession:
            self.session = cache
        else:
            self.session = requests.Session()

        # MongoDB database to store scraped data in
        self.db: Union[Database, None] = kwargs.get('db', None)

    


    def __del__(self):
        self.session.close()



    def scrape_and_upsert(self, **kwargs) -> None:
        """
        Scrapes questions and their answers from Stack Overflow and inserts
        them into the database. If the question already exists in the database,
        it will be updated.

        A `db` keyword argument must have been provided to the constructor,
        otherwise this method will raise an exception.
        
        ## Keyword arguments:

        - `drop`     -- (bool) If True, drop the `question` and `answer`
                        collections before scraping. (default: False)
        - `pagesize` -- (int) The number of questions to retrieve per API call. Must
                        be 1<= `pagesize` <= 100. (default: 100)
        - `page`     -- (int) The page of questions to start at. Must be > 0.
                        (default: 1)
        - `api_key`  -- (str | None) The Stack Overflow API key to use. (default: None)
        - `maxpages` -- (int) The maximum number of question batches to scrape,
                        each of size `pagesize`. (default: 10)
        """

        drop: bool = kwargs.get('drop', False)

        if self.db is None:
            raise Exception('No database provided')

        # Drop the question and answer collections if requested
        if drop:
            print('Dropping question and answer collections')
            self.db.questions.drop()
            self.db.answers.drop()

        # Iterate over each questions batch obtained from the API
        for page in self.get_questions(**kwargs):
            assert type(page) is list

            # Remove questions with no answers. Also, questions with low scores are less likely
            # to have useful answers, it's probably just someone insulting the poster for
            # being a noob.
            page = list(filter(lambda q: q['answer_count'] > 0 and q['score'] > 0, page))

            # Mark and store questions with no quality answers
            marked_questions: List[str] = []
            answers_to_store: List[Dict] = []

            time_start = time.time()
            print(f'Scraping {len(page)} questions ', end='')
            for q in page:

                # Scrape answers for each question
                try:
                    answers = self.scrape_answers(q['link'])
                except Exception as e:
                    link = q['link']
                    e.args += (f'Failed to scrape question: {link}',)
                    raise e

                # Mark the question for removal if it has no quality answers
                if not len(answers):
                    print('x', end = '')
                    marked_questions.append(q['question_id'])
                    continue
                else:
                    print('.', end = '', flush = True)

                # Add the question_id as a foreign key to the answers
                for a in answers:
                    a['question_id'] = q['question_id']

                answers_to_store.extend(answers)

                # Sleep for a bit to avoid hitting the API too hard
                time.sleep(0.6 + random.random() / 2)

            print('')

            # Remove questions with no quality answers
            if len(marked_questions):
                print(f'Removing {len(marked_questions)} questions with no quality answers')
                page = list(filter(lambda q: q['question_id'] not in marked_questions, page))

            # Store the questions
            questions_upsert = [UpdateOne({'_id': q['question_id']}, {'$set': q}, upsert=True) for q in page]
            questions_result = self.db.questions.bulk_write(questions_upsert)

            # Store the answers
            answers_upsert = [UpdateOne({'_id': a['answer_id']}, {'$set': a}, upsert=True) for a in answers_to_store]
            answers_result = self.db.answers.bulk_write(answers_upsert)

            duration = time.time() - time_start
            print(f'Stored {questions_result.upserted_count} questions and {answers_result.upserted_count} answers in {duration:,.2f} seconds')



    def get_questions(self, **kwargs) -> Generator[List[Dict], None, None]:
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

        * `pagesize` -- The number of questions to retrieve per API call. Must
                        be 1<= `pagesize` <= 100. (default: 100) 
        * `page`     -- The page of questions to start at. Must be > 0.
                        (default: 1)
        * `maxpages` -- The maximum number of pages to retrieve. Must be > 0.
                        (default: 10)
        * `api_key`  -- The Stack Overflow API key to use. (default: None)
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

            print(f'Requesting page #{page}')
            # Returns a Common Wrapper Object
            # https://api.stackexchange.com/docs/wrapper
            r = self.session.get('https://api.stackexchange.com/2.3/questions', params=query_params)

            content_type = r.headers.get('content-type', '')
            content_length = r.headers.get('content-length', 0)

            if r.status_code > 299:
                if content_length == 0:
                    r.raise_for_status()

                elif 'json' in content_type:
                    error_json = r.json()
                    raise requests.HTTPError(f'{r.status_code} {r.reason} API returned error {error_json["error_id"]}: {error_json["error_message"]}')
                    
                else:
                    raise requests.HTTPError(f'{r.status_code} {r.reason}: {r.text}')

                    
            assert 'json' in content_type # We're expecting JSON back

            # Yield each question in the response
            body = r.json()
            assert 'items' in body
            assert isinstance(body['items'], list)
            yield body['items']

            # Check if we're done
            quota_remaining = body['quota_remaining']
            quota_max = body['quota_max']
            has_more: bool = body['has_more']
            done = not has_more or body['quota_remaining'] <= 0
            print(f'Got {pagesize} questions from page #{page} (#pages: {requests_made}/{maxpages}, quota: {quota_remaining}/{quota_max})')

            requests_made += 1
            page += 1
            # print('\r', f'Got {pagesize} questions from page #{page} (quota: {quota_remaining}/{quota_max})', end='')


            # Check if we need to back off before sending more requests. Only necessary if we're not done.
            backoff = body.get('backoff', 0)
            if not done and backoff > 0:
                print(f'Backoff requested, sleeping for {backoff} seconds')
                time.sleep(backoff)



    def scrape_answers(self, url: str) -> List[Dict]:
        """
        Scrapes the answers for a given question URL.

        Given a URL to a StackOverflow question page, this method will return
        a list of answer objects as dicts. If the question has no answers, an
        empty list will be returned.
        
        Each answer object contains the following keys:
        * `answer_id`   -- The ID of the answer (int). This is the same ID used
                           in the StackOverflow API, and is therefore unique to
                           the answer.

        * `snippets`    -- All code snippets contained in the answer, joined by
                           newlines.

        * `score`       -- The score of the answer (int). Upvotes minus downvotes.

        * `is_accepted` -- Whether the OP accepted the  answer is accepted (bool).

        * `source`      -- URL to the answer (str).

        * `author_id`   -- The User ID of the author (int | None). If answered 
                           anonymously, this will be None. If answered by
                           the community, this will be -1.

        * `author_name` -- The name of the author (str). May be `'anonymous'`
                           or `'community'`.

        * `page_pos`    -- The position of the answer on the page (int). Value
                           is [0, num_answers)

        * `is_highest_score` -- Whether the answer has the highest score among
                                all other answers (bool).

        * `question_has_highest_accepted_answer` -- Whether any of the answers
                                                    to the question have the 
                                                    highest score and are also
                                                    accepted by the OP (bool).
        ## Arguments:
        - `url` -- The URL of the question to scrape answers for.

        ## Returns:
        A list of answer objects as dicts.
        """

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

            snippets: str =  '\n'.join([code_block.text for code_block in snippet_elems])
            snippets = snippets.strip()
            assert snippets

            # Contains the user name and id of the answerer
            author_id, author_name = self._scrape_user_details(answer)

            answer_data = {
                # 'question_id': question_id,
                'snippets': snippets,
                'score': int(answer['data-score']),
                'answer_id': answer_id,
                'page_pos': int(answer['data-position-on-page']),
                'is_highest_scored': answer['data-highest-scored'] == '1',
                'question_has_highest_accepted_answer': answer['data-question-has-accepted-highest-score'] == '1',
                'is_accepted': 'accepted-answer' in answer['class'],
                'source': f'https://stackoverflow.com/a/{answer_id}',
                'author_id': author_id,
                'author_username': author_name,
            }

            answers_parsed.append(answer_data)

        return answers_parsed

    def _scrape_user_details(self, answer: Tag) -> Tuple[Union[int, None], str]:
        assert answer

        # Extract the answer author's user id. Anonymous users have no user id
        user_details = answer.select('.post-signature .user-details > a')
        if user_details is None or len(user_details) == 0:
            return None, 'anonymous'
        else:
            try:
                user_details = list(user_details)
                # TODO: unravel user_details list

                for details in user_details:

                    # assert 'href' in details, 'No href attribute found in user details'

                    if 'users' in details['href']:
                        # has shape /user/:id/:name or /user/:id. In the latter
                        # case, the name is in the text of the anchor tag
                        link = details['href']
                        link = link.strip(' /')
                        link = [seg.strip() for seg in link.split('/')]
                        assert len(link) > 1 and 'users' in link[0]
                        link = link[1:]
                        user_id = int(link.pop(0))
                        if len(link) > 0:
                            user_name = link.pop(0)
                        else:
                            user_name = details.text.strip()

                        assert user_id is not None and user_name is not None
                        return user_id, user_name

                    # Skip links to community wiki
                    elif 'collectives' in details['href']:
                        user_details.extend(details.select('a'))
                        continue

                    # Skip history revision links
                    elif 'title' in details.attrs and 'history' in details.attrs['title']:
                        user_details.extend(details.select('a'))
                        continue

                print(f'WARNING: Could not find user details for answer {answer.prettify()[0:64]}...')
                return None, 'unknown'

            except Exception as e:
                e.args += (f'Failed to parse user details from {details.prettify()}',)
                raise e