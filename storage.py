import json
import os

DB_FILE = "users.json"

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"users": {}, "sponsors": []}, f)

def load():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def get_user(db, uid, username):
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": uid,
            "username": username,
            "balance": 0,
            "refs": 0,
            "ref_by": None,
            "state": None
        }
        save(db)
    return db["users"][uid]
