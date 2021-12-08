# Test script to see if scrape/stack.py works
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from scrape.stack import StackOverflowScraper

load_dotenv()

def get_mongo_client() -> MongoClient:
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        raise Exception('MONGO_URI not set')
    client = MongoClient(mongo_uri, tls=True)
    return client
# _mongo_uri = 'mongodb+srv://admin:<password>@cmsc320-final-tutorial.i5dh9.mongodb.net/myFirstDatabase?retryWrites=true&w=majority'
# print(_mongo_uri)

client = get_mongo_client()
db = client['stackOverflowDB']
stack = StackOverflowScraper(db=db)

stack.scrape_and_upsert(drop=False, page=134, maxpages=100)