from pymongo import MongoClient
from config import settings

mongo_client = MongoClient(settings.MONGODB_URI)
db = mongo_client[settings.DB_NAME]
