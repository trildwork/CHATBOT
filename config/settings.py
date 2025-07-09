import os
from dotenv import load_dotenv
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_JOB_EVENTS_TOPIC = os.getenv("KAFKA_JOB_EVENTS_TOPIC")
