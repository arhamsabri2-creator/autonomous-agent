import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("agent-memory")

bad_ids = [
    "45ccfa1b-48a4-4a64-b5ba-f10ea3e258be",
    "ca171035-4d2b-4f34-9dda-49fb36446d27"
]

index.delete(ids=bad_ids)
print("Deleted bad memories successfully")
