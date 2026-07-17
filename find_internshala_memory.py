import os
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

load_dotenv()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("agent-memory")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

query = "search for AI job and apply for the first one on internshala"
embedding = openai_client.embeddings.create(model="text-embedding-3-small", input=query).data[0].embedding

results = index.query(vector=embedding, top_k=5, include_metadata=True)
for match in results["matches"]:
    print("ID:", match["id"])
    print("Goal:", match["metadata"].get("goal", ""))
    print("Score:", match["score"])
    print("---")
