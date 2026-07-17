import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("agent-memory")

bad_ids = [
    "e680ceb0-f58f-4b13-bb53-8b6bfdf98cc9",
    "9dac42bb-8f83-4091-8844-2a3b7d8587e1"
]

index.delete(ids=bad_ids)

print("Deleted:", bad_ids)