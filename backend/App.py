from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import requests
from datetime import datetime, timedelta

app = FastAPI()

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["news_db"]
collection = db["article"]

def setup_ttl_index():
    """Create TTL index to auto-delete old articles"""
    try:
        ttl_hours = int(os.getenv("NEWS_TTL_HOURS", "24"))
        
        collection.create_index(
            [("cached_at", 1)], 
            expireAfterSeconds=ttl_hours * 60 * 60  
        )
        print(f"✅ TTL index created: Articles will auto-delete after {ttl_hours} hours")
    except Exception as e:
        print(f"⚠️ TTL index setup failed: {e}")

setup_ttl_index()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

article_vectors = {}

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

CACHE_DURATION_HOURS = 6  

def is_news_fresh():
    """Check if cached news is still fresh"""
    latest_article = collection.find_one({}, sort=[("publishedAt", -1)])
    if not latest_article:
        return False
    
    try:
        latest_date = datetime.fromisoformat(latest_article["publishedAt"].replace("Z", "+00:00"))
        time_diff = datetime.now(latest_date.tzinfo) - latest_date
        return time_diff.total_seconds() < (CACHE_DURATION_HOURS * 3600)
    except:
        return False

def fetch_fresh_news():
    """Fetch fresh news from NewsAPI"""
    try:
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = (
            f'https://newsapi.org/v2/everything?'
            f'q=AI+ML&'
            f'from={from_date}&'
            f'language=en&'
            f'sortBy=publishedAt&'
            f'apiKey={NEWS_API_KEY}'
        )
        response = requests.get(url).json()
        
        if "articles" in response:
            new_articles = []
            for article in response["articles"]:
                data = {
                    "title": article["title"],
                    "description": article["description"],
                    "url": article["url"],
                    "source": article["source"]["name"],
                    "publishedAt": article["publishedAt"],
                    "content": article["content"],
                    "cached_at": datetime.now().isoformat()
                }


                if collection.count_documents({"url": data["url"]}) == 0:
                    collection.insert_one(data)
                    new_articles.append(data)
            
            return new_articles
        return []
    except Exception as e:
        print(f"Error fetching fresh news: {e}")
        return []

class ChatRequest(BaseModel):
    article_id: str
    article_text: str
    question: str

@app.get("/api/news")
async def get_news(category: str = "Latest", search: str = None, refresh: bool = False):
    try:
        if refresh or not is_news_fresh():
            fetch_fresh_news()
        
        query = {}
        
        if search:
            query = {
                "$or": [
                    {"title": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]
            }
        
        articles = list(collection.find(query, {"_id": 0}).sort("publishedAt", -1).limit(50))
        
        # Add cache info for frontend
        cache_info = {
            "is_fresh": is_news_fresh(),
            "last_updated": None
        }
        
        # Get last update time
        latest = collection.find_one({}, sort=[("cached_at", -1)])
        if latest and "cached_at" in latest:
            cache_info["last_updated"] = latest["cached_at"]
        
        return {
            "articles": articles,
            "cache_info": cache_info
        }

    except Exception as e:
        return {"error": str(e)}

@app.get("/api/news/refresh")
async def refresh_news():
    """Force refresh news from API"""
    try:
        new_articles = fetch_fresh_news()
        return {
            "message": f"Refreshed {len(new_articles)} new articles",
            "new_articles_count": len(new_articles)
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/news/cleanup")
async def cleanup_old_news(hours: int = 24):
    """Manually delete articles older than specified hours"""
    try:
        cutoff_date = datetime.now() - timedelta(hours=hours)
        result = collection.delete_many({
            "cached_at": {"$lt": cutoff_date.isoformat()}
        })
        return {
            "message": f"Deleted {result.deleted_count} articles older than {hours} hour{'s' if hours != 1 else ''}",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/news/stats")
async def get_news_stats():
    """Get statistics about news collection"""
    try:
        total_articles = collection.count_documents({})
        
        # Articles by age (hours-based)
        now = datetime.now()
        stats = {
            "total_articles": total_articles,
            "articles_by_age": {
                "last_hour": collection.count_documents({
                    "cached_at": {"$gte": (now - timedelta(hours=1)).isoformat()}
                }),
                "last_24_hours": collection.count_documents({
                    "cached_at": {"$gte": (now - timedelta(hours=24)).isoformat()}
                }),
                "older_than_24_hours": collection.count_documents({
                    "cached_at": {"$lt": (now - timedelta(hours=24)).isoformat()}
                })
            }
        }
        return stats
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/evaluation/stats")
async def get_evaluation_stats():
    """Get RAG evaluation statistics"""
    # This would store evaluation metrics over time
    # For now, return explanation of metrics
    return {
        "metrics_explanation": {
            "context_relevance": "How well retrieved chunks match the question (0-1)",
            "answer_grounding": "How well answer is based on retrieved context (0-1)",
            "completeness": "How completely answer addresses the question (0-1)",
            "overall_score": "Weighted combination of all metrics (0-1)"
        },
        "scoring_weights": {
            "context_relevance": 0.3,
            "answer_grounding": 0.4,
            "completeness": 0.3
        },
        "quality_thresholds": {
            "excellent": 0.8,
            "good": 0.6,
            "fair": 0.4,
            "poor": 0.2
        }
    }

@app.post("/chat")
def chat_with_article(req: ChatRequest):
    if req.article_id not in article_vectors:
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = splitter.create_documents([req.article_text])

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectordb = FAISS.from_documents(docs, embeddings)
        article_vectors[req.article_id] = vectordb
    else:
        vectordb = article_vectors[req.article_id]

    def get_optimal_k(article_text):
        word_count = len(article_text.split())
        if word_count < 300:
            return 2
        elif word_count < 800:
            return 3
        elif word_count < 1500:
            return 5
        else:
            return 7

    retriever = vectordb.as_retriever(search_kwargs={"k": get_optimal_k(req.article_text)})
    llm = ChatGroq(model="llama-3.1-8b-instant", api_key=GROQ_API_KEY, temperature=0.7)
    
    template = """Use the following pieces of context to answer the question at the end.
    If you don't know the answer, just say that you don't know, don't try to make up an answer but try to respond to simple greeting and basic query other than context.
    Keep the answer concise and relevant to the question.
    If the context is empty or irrelevant, say "I couldn't find relevant information in this article."

    Context: {context}

    Question: {question}

    Helpful Answer:"""
    
    prompt = PromptTemplate.from_template(template)
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    answer = rag_chain.invoke(req.question)
    
    return {
        "answer": answer
    }


# Optional: Run server directly from Python file
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False) # here the auto reload is off if we run the 
                                                              # python app.py if we make changes to the code it dont reload automatically
                                                              #  to do that use the uvicorn App:app --reload --port 8000


