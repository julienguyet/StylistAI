import pandas as pd
import numpy as np
from pymongo import MongoClient, UpdateOne
from dotenv import dotenv_values
from tqdm import tqdm

env_path = "/workspace/.env"
config = dotenv_values(env_path)
client = MongoClient(config['MONGO_CONNECTION_STRING'])
db = client["stylistai"]
dashline = "---" * 15

def row_to_doc(row: dict) -> dict:
    """
    Convert a dataframe row to a Mongo ready document.
    """
    
    doc = dict(row)

    def is_missing(value) -> bool:
        if value is None:
            return True
        if isinstance(value, (list, dict, tuple, set)):
            return False
        missing = pd.isna(value)
        if isinstance(missing, (list, np.ndarray)):
            return False
        return bool(missing)

    for k, v in list(doc.items()):
        if is_missing(v):
            doc[k] = None

    pa = doc.get("purchased_articles")
    if pa is None or is_missing(pa):
        doc["purchased_articles"] = []
    elif not isinstance(pa, list):
        doc["purchased_articles"] = list(pa)

    return doc

print("Starting Job: creating Customers Collection in Mongo")
print(dashline)

print("Loading dataset...")
csv_path = "/data/processed/customers_df.csv"
chunksize = 50000
customers_df = pd.read_csv(csv_path, chunksize=chunksize)
print("Successful! Now moving to writing operation...")
print(dashline)

print("Initiating collection in Mongo")
customers_collection = db["customers"]
customers_collection.create_index("customer_id", unique=True)
print(dashline)

print("Now turning dataframe rows into documents and upserting in batches")
matched = 0
modified = 0
upserted = 0

with tqdm() as pbar:
    for chunk in customers_df:
        docs = [row_to_doc(r) for r in chunk.to_dict(orient="records")]
        if not docs:
            continue
        operations = [
            UpdateOne({"customer_id": d["customer_id"]}, {"$set": d}, upsert=True)
            for d in docs]
        result = customers_collection.bulk_write(operations, ordered=False)
        matched += result.matched_count
        modified += result.modified_count
        upserted += len(result.upserted_ids) if result.upserted_ids else 0
        pbar.update(len(docs))

print(dashline)
print("Job Done!")
print("")
print({"matched": matched,
    "modified": modified,
    "upserted": upserted
    })
print(dashline)
print("Now exiting process.")
