from motor.motor_asyncio import AsyncIOMotorClient

mongo_uri = "mongodb://localhost:27017"
db_name = "notes_db"

conn = AsyncIOMotorClient(mongo_uri)

db = conn[db_name]
notes_collection = db["notes"]
