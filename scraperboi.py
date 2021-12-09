# Test script to see if scrape/stack.py works
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from scrape.stack import StackOverflowScraper
from urllib.parse import quote_plus

load_dotenv()

page_start: int = 650
# Connect to MongoDB
def get_mongo_client() -> MongoClient:

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

    client = MongoClient(mongo_uri, tls=True)
    return client

client = get_mongo_client()
db = client['stackOverflowDB']
db.command('ping')
stack = StackOverflowScraper(db=db)

stack.scrape_and_upsert(drop=False, page=page_start, maxpages=100)