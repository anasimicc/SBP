import csv
import pandas as pd
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["SBP"]
collection = db["steam_games"]
collection.drop()

rows = []
with open("games.csv", encoding="utf-8-sig", newline="") as f:
    reader = csv.reader(f, quotechar='"', doublequote=True, skipinitialspace=True)
    header = next(reader)
    header.insert(16, "Support email 2")  # FIX
    for row in reader:
        if len(row) == len(header):
            rows.append(row)

df = pd.DataFrame(rows, columns=header)
df.columns = df.columns.str.strip()
df = df.dropna(subset=["AppID"])

def safe_int(x):
    try:
        if pd.isna(x): return 0
        return int(str(x).split(".")[0])
    except: return 0

def safe_float(x):
    try:
        if pd.isna(x): return 0.0
        return float(x)
    except: return 0.0

def split_list(x):
    if pd.isna(x): return []
    return [i.strip() for i in str(x).split(",") if i.strip()]

def to_bool(x):
    return str(x).strip().lower() == "true"

batch = []
batch_size = 5000
counter = 1

for _, row in df.iterrows():
    doc = {
        "_id": counter,
        "app_id": safe_int(row.get("AppID", 0)),
        "name": str(row.get("Name", "")),
        "release_date": str(row.get("Release date", "")),
        "price": safe_float(row.get("Price", 0)),
        "required_age": safe_int(row.get("Required age", 0)),
        "dlc_count": safe_int(row.get("DiscountDLC count", 0)),
        "platforms": {
            "windows": to_bool(row.get("Windows", False)),
            "mac": to_bool(row.get("Mac", False)),
            "linux": to_bool(row.get("Linux", False))
        },
        "owners": {
            "estimated": str(row.get("Estimated owners", "")),
            "peak_ccu": safe_int(row.get("Peak CCU", 0))
        },
        "reviews": {
            "positive": safe_int(row.get("Positive", 0)),
            "negative": safe_int(row.get("Negative", 0)),
            "metacritic_score": safe_int(row.get("Metacritic score", 0)),
            "user_score": safe_float(row.get("User score", 0)),
            "recommendations": safe_int(row.get("Recommendations", 0))
        },
        "developers": split_list(row.get("Developers", "")),
        "publishers": split_list(row.get("Publishers", "")),
        "categories": split_list(row.get("Categories", "")),
        "genres": split_list(row.get("Genres", "")),
        "tags": split_list(row.get("Tags", "")),
        "supported_languages": split_list(row.get("Supported languages", "")),
        "audio_languages": split_list(row.get("Full audio languages", "")),
        "website": str(row.get("Website", "")),
        "description": str(row.get("About the game", ""))
    }

    batch.append(doc)
    counter += 1

    if len(batch) >= batch_size:
        collection.insert_many(batch)
        batch = []

if batch:
    collection.insert_many(batch)

print("DONE")
print("Inserted:", collection.count_documents({}))