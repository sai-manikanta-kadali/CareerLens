"""Seed the MongoDB jobs collection from data/jobs.json."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


def main():
    load_dotenv()
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI is missing. Configure your .env file.")

    project_root = Path(__file__).resolve().parents[1]
    with (project_root / "data" / "jobs.json").open(encoding="utf-8") as file:
        jobs = json.load(file)

    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    try:
        client.admin.command("ping")
        collection = client["internship_research"]["jobs"]
        collection.create_index("source_url", unique=True)
        inserted = 0
        updated = 0

        for job in jobs:
            source_url = job.get("source_url")
            if not source_url:
                continue
            result = collection.update_one(
                {"source_url": source_url},
                {"$set": job},
                upsert=True,
            )
            inserted += int(result.upserted_id is not None)
            updated += int(result.modified_count > 0)

        print(f"Seed complete: {inserted} inserted, {updated} updated.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
