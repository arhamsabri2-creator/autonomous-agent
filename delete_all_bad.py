import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("agent-memory")

bad_ids = [
    "d3358bf4-a224-4c76-aeed-3db25131ce87",
    "548bf37d-66f5-45b3-b572-ef28972e738c"
]

index.delete(ids=bad_ids)
print("Deleted successfully")
