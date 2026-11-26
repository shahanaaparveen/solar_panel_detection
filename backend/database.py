from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db_name = os.getenv("DB_NAME", "solar_inspect")

try:
    # Attempt connecting to MongoDB with a short timeout
    real_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
    real_client.admin.command("ping")
    client = real_client
    print(f"[Database] Connected to MongoDB at {mongo_uri}")
except Exception as e:
    print(f"[Database] MongoDB not accessible ({e}). Initializing in-memory fallback database.")
    import mongomock
    client = mongomock.MongoClient()

db = client[db_name]

# Collections
projects_col    = db["projects"]
detections_col  = db["detections"]
reports_col     = db["reports"]

