import requests
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load keys
load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client["news_db"]
collection = db["articles"]

# Fetch AI/ML news
from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
url = (
    f'https://newsapi.org/v2/everything?'
    f'q=AI+ML&'
    f'from={from_date}&'
    f'language=en&'
    f'sortBy=publishedAt&'
    f'apiKey={NEWS_API_KEY}'
    )
response = requests.get(url).json()
output={}
if "articles" in response:
    for article in response["articles"]:
        data = {
            "title": article["title"],
            "description": article["description"],
            "url": article["url"],
            "source": article["source"]["name"],
            "publishedAt": article["publishedAt"],
            "content": article["content"]
        }
        output[article["title"]]=data
        # Avoid duplicates
        if collection.count_documents({"url": data["url"]}) == 0:
            collection.insert_one(data)
            print(f"Inserted: {data['title']}")
    print(len(output))
else:
    print("Error fetching news:", response)
