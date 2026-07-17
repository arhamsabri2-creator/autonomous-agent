import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("agent-memory")

index.delete(ids=["58a9c37a-4e63-40de-9b7f-1464ae18f649"])
print("Deleted successfully")
