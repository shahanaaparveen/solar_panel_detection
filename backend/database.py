from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]

# Collections
projects_col    = db["projects"]
detections_col  = db["detections"]
reports_col     = db["reports"]
