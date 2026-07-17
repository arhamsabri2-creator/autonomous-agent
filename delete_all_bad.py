import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("agent-memory")

bad_ids = [
    "191ac536-b699-4e94-975e-733bb115c136",
    "1f77cbb4-9ce2-4fe1-92b9-c4716762d1d5",
    "6d393e83-1037-4e5e-bc8d-c40e4ca491e5"
]

index.delete(ids=bad_ids)
print("Deleted successfully")
