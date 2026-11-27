"""MongoDB collections with an explicitly reported development fallback."""
import os
import logging
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db_name = os.getenv("DB_NAME", "solar_inspect")
storage_mode = "mongodb"
storage_error = None
try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
    client.admin.command("ping")
except Exception as exc:
    storage_mode = "in_memory_development"
    storage_error = str(exc)
    import mongomock
    client = mongomock.MongoClient()
db = client[db_name]
projects_col = db["projects"]
detections_col = db["detections"]
reports_col = db["reports"]
jobs_col = db["analysis_jobs"]
panels_col = db["panel_detections"]
findings_col = db["findings"]
images_col = db["images"]
registrations_col = db["image_registrations"]
model_runs_col = db["model_runs"]
mappings_col = db["panel_mappings"]

logger = logging.getLogger("solar_inspect.database")
index_errors = {}
index_specs = [
    (projects_col, [("createdAt", -1)], {"name": "project_created_at"}),
    (jobs_col, [("jobId", 1)], {"unique": True, "name": "job_id_unique"}),
    (jobs_col, [("projectId", 1), ("requestId", 1)], {"unique": True, "partialFilterExpression": {"requestId": {"$exists": True}}, "name": "job_request_unique"}),
    (detections_col, [("jobId", 1), ("imageId", 1)], {"unique": True, "name": "job_image_result_unique"}),
    (panels_col, [("projectId", 1), ("imageId", 1)], {"unique": True, "name": "project_image_panel_unique"}),
    (findings_col, [("projectId", 1), ("findingId", 1)], {"unique": True, "name": "project_finding_unique"}),
    (reports_col, [("projectId", 1), ("createdAt", -1)], {"name": "project_report_date"}),
    (images_col, [("imageId", 1)], {"unique": True, "name": "image_id_unique"}),
    (images_col, [("projectId", 1), ("imageType", 1), ("sha256", 1)], {"unique": True, "partialFilterExpression": {"sha256": {"$exists": True}}, "name": "project_image_hash_unique"}),
    (registrations_col, [("projectId", 1), ("referenceImageId", 1), ("movingImageId", 1)], {"unique": True, "name": "registration_pair_unique"}),
    (model_runs_col, [("modelRunId", 1)], {"unique": True, "name": "model_run_unique"}),
    (mappings_col, [("projectId", 1)], {"unique": True, "name": "project_mapping_unique"}),
]
for collection, keys, options in index_specs:
    try:
        collection.create_index(keys, **options)
    except Exception as exc:
        index_errors[options["name"]] = str(exc)
        logger.exception("Failed to create database index %s", options["name"])
