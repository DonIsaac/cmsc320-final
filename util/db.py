import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.cursor import Cursor
from pymongo.collection import Collection
from scrape.types import StackOverflowAnswer, StackOverflowQuestion
from urllib.parse import quote_plus
from typing import Generator, Any

load_dotenv()
class Database:
    """
    A utility class that wraps a MongoDB database.
    """

    # Connect to MongoDB
    def __init__(self):
        """
        Creates a new Database object.

        This object is used to interact with the MongoDB database. Upon
        initialization, it will connect to the database and create a
        collection if it does not already exist.
        """

        # A MongoDB connection string _must_ be provided
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            raise Exception('MONGO_URI not set')

        # URI may either be a fully usable mongo connection string, or a printf-style string
        # where the username and password are specified as %s and %s respectively
        # e.g. mongodb+srv://%s:%s@mongodb.mydomain.com:27017/someDatabase
        # See: 
        #   https://pymongo.readthedocs.io/en/stable/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient
        #   https://docs.mongodb.com/manual/reference/connection-string/
        user = os.getenv('MONGO_USERNAME') or os.getenv('MONGO_PUBLIC_KEY')
        pw = os.getenv('MONGO_PASSWORD') or os.getenv('MONGO_PRIVATE_KEY')

        if user and pw:
            mongo_uri = mongo_uri % ( quote_plus(user), quote_plus(pw))
        else:
            assert not user and not pw, 'MONGO_USERNAME and MONGO_PASSWORD must both be set or both be unset'

        self._client = MongoClient(mongo_uri, tls=True)
        self._db = self._client['stackOverflowDB']
        self._questions = self._db['questions']
        self._answers = self._db['answers']

    @property
    def answers(self) -> Collection:
        return self._answers

    @property
    def questions(self) -> Collection:
        return self._questions
  
    def get_questions(self, page_num: int = 1, **kwargs: int) -> Generator[StackOverflowQuestion, None, None]:
        """
        Returns a generator of questions from the StackOverflow database

        # Arguments
            page_num: The starting page number to retrieve questions from. Page
                      numbers are 1-indexed. Defaults to 1.

        ## Keyword Arguments
            page_size: The number of questions to retrieve per page. Defaults to 100.
            
        """

        return self._paginate(self._questions, page_num, **kwargs)

    def get_answers(self, page_num: int = 1, **kwargs: int) -> Generator[StackOverflowAnswer, None, None]:
        """
        Returns a generator of answers from the StackOverflow database

        # Arguments
            page_num: The starting page number to retrieve questions from. Page
                      numbers are 1-indexed. Defaults to 1.

        ## Keyword Arguments
            page_size: The number of questions to retrieve per page. Defaults to 100.
            
        """

        return self._paginate(self._answers, page_num, **kwargs)

    def get_all_answers(self) -> Generator[StackOverflowAnswer, None, None]:
        """
        Returns a generator of all answers from the StackOverflow database
        """

        cursor =  self._answers.find()
        for doc in cursor:
            yield doc

    def _paginate(self, collection: Collection, page_num: int = 1, **kwargs: int) -> Generator[Any, None, None]:
        assert type(page_num) == int and page_num > 0, 'page_num must be a positive integer'

        page_size = kwargs.get('page_size', 100) # How many pages to return
        assert type(page_size) == int and page_size > 0, 'page_size must be a positive integer'

        # Calculate number of documents to skip
        skips = page_size * (page_num - 1)

        # Skip and limit
        cursor: Cursor = collection.find().skip(skips).limit(page_size)
        for doc in cursor:
            yield doc
