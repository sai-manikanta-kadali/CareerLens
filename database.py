
import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Load environment variables
load_dotenv()


def create_mongo_client():

    # Read connection URI
    mongodb_uri = os.getenv("MONGODB_URI")

    if not mongodb_uri:
        raise RuntimeError("MongoDB URI is missing")

    # Create MongoDB client
    client = MongoClient(
        mongodb_uri,
        server_api=ServerApi("1"),
        serverSelectionTimeoutMS=10000
    )

    return client

