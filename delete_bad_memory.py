import os
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("agent-memory")

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text):
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


query_embedding = get_embedding("Log into the test login page")

results = index.query(
    vector=query_embedding,
    top_k=5,
    include_metadata=True
)

for match in results["matches"]:
    goal = match["metadata"].get("goal", "")
    print(f"ID: {match['id']}")
    print(f"Goal: {goal}")
    print(f"Score: {match['score']}")
    print("---")