import json
import chromadb
from crewai.tools import tool

_chroma_client = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.Client()
    return _chroma_client

@tool("Store Recommendations In Memory")
def store_recommendations_in_memory(recommendations_json: str, run_id: str) -> str:
    """
    Stores recommended actions within the local ChromaDB memory system.
    """
    try:
        data = json.loads(recommendations_json)
        recs = data.get("recommendations", [])
        
        if not recs:
            return json.dumps({"status": "no recommendations to store"})
            
        collection = get_chroma_client().get_or_create_collection(name="hvac_recommendations")
        
        ids = []
        documents = []
        metadatas = []
        
        for i, rec in enumerate(recs):
            doc = f"Action: {rec.get('action', '')} | Rationale: {rec.get('rationale', '')}"
            meta = {
                "run_id": run_id,
                "category": rec.get("category", "General"),
                "priority_score": float(rec.get("priority_score", 0.0)),
                "timestamp": run_id
            }
            ids.append(f"{run_id}_rec_{i}")
            documents.append(doc)
            metadatas.append(meta)
            
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        return json.dumps({"status": "success", "stored_count": len(recs)})
        
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool("Query Similar Past Recommendations")
def query_similar_past_recommendations(query: str) -> str:
    """
    Queries past recommendations using vector storage.
    """
    try:
        collection = get_chroma_client().get_or_create_collection(name="hvac_recommendations")
        if collection.count() == 0:
            return json.dumps({"status": "success", "results": {"documents": []}})
            
        results = collection.query(query_texts=[query], n_results=min(3, collection.count()))
        return json.dumps({
            "status": "success",
            "results": results
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})
