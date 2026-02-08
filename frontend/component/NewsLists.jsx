import React, { useEffect, useState } from "react";
import {useNavigate} from 'react-router-dom';
import axios from "axios";
import "./NewsList.css";

const categories = ["Latest", "Technology", "Politics", "Sports", "Health", "Business", "Education"];

const NewsList = () => {
  const navigate = useNavigate();
  const [articles, setArticles] = useState([]);
  const [search, setSearch] = useState("");
  const [heading, setHeading] = useState("Latest News");
  const [cacheInfo, setCacheInfo] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [stats, setStats] = useState(null);
  const [showStats, setShowStats] = useState(false);

  const fetchNews = (query, type = "category", forceRefresh = false) => {
    let url = "http://localhost:8000/api/news";
    const params = new URLSearchParams();
    
    if (type === "category") {
      params.append("category", query);
      setHeading(`${query} News`);
    } else {
      params.append("search", query);
      setHeading(`Search Results for "${query}"`);
    }
    
    if (forceRefresh) {
      params.append("refresh", "true");
    }
    
    url += `?${params.toString()}`;

    setIsRefreshing(forceRefresh);
    axios
      .get(url)
      .then((res) => {
        setArticles(res.data.articles || res.data); // Handle both old and new format
        setCacheInfo(res.data.cache_info || null);
      })
      .catch((err) => console.log(err))
      .finally(() => setIsRefreshing(false));
  };

  const handleRefresh = () => {
    fetchNews("Latest", "category", true);
  };

  const fetchStats = () => {
    axios.get("http://localhost:8000/api/news/stats")
      .then((res) => {
        setStats(res.data);
        setShowStats(true);
      })
      .catch((err) => console.log(err));
  };

  const handleCleanup = (hours) => {
    if (window.confirm(`Delete articles older than ${hours} hour${hours !== 1 ? 's' : ''}?`)) {
      axios.get(`http://localhost:8000/api/news/cleanup?hours=${hours}`)
        .then((res) => {
          alert(res.data.message);
          fetchStats(); // Refresh stats after cleanup
          fetchNews("Latest", "category"); // Refresh news list
        })
        .catch((err) => console.log(err));
    }
  };

  useEffect(() => {
    fetchNews("Latest", "category"); // show latest news by default
  }, []);

  return (
    <div className="news-page">

      <div className="sidebar">
        <h3>Categories</h3>
        <ul>
          {categories.map((cat) => (
            <li key={cat} onClick={() => fetchNews(cat, "category")}>
              {cat}
            </li>
          ))}
        </ul>

        <div className="search-box">
          <input
            type="text"
            placeholder="Search news..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button onClick={() => fetchNews(search, "search")}>Search</button>
        </div>

        <div className="stats-section">
          <h4>📊 Database Stats</h4>
          <button onClick={fetchStats} className="stats-btn">
            {showStats ? "🔄 Refresh Stats" : "📊 Get Stats"}
          </button>
          
          {showStats && stats && (
            <div className="stats-display">
              <p><strong>Total Articles:</strong> {stats.total_articles}</p>
              <p><strong>Last Hour:</strong> {stats.articles_by_age.last_hour || 0}</p>
              <p><strong>Last 24 Hours:</strong> {stats.articles_by_age.last_24_hours || 0}</p>
              <p><strong>Older than 24 Hours:</strong> {stats.articles_by_age.older_than_24_hours || 0}</p>
              
              <div className="cleanup-buttons">
                <h5>🗑️ Cleanup Options:</h5>
                <button onClick={() => handleCleanup(1)} className="cleanup-btn">
                  Clean &gt; 1 hour
                </button>
                <button onClick={() => handleCleanup(6)} className="cleanup-btn">
                  Clean &gt; 6 hours
                </button>
                <button onClick={() => handleCleanup(12)} className="cleanup-btn">
                  Clean &gt; 12 hours
                </button>
                <button onClick={() => handleCleanup(24)} className="cleanup-btn">
                  Clean &gt; 24 hours
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="news-container">
        <div className="news-header">
          <h1>{heading}</h1>
          <div className="refresh-section">
            <button 
              className="refresh-btn" 
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              {isRefreshing ? "Refreshing..." : "🔄 Refresh News"}
            </button>
            {cacheInfo && (
              <span className="cache-info">
                {cacheInfo.is_fresh ? "✅ Fresh" : "⚠️ Stale"} 
                {cacheInfo.last_updated && 
                  ` • Updated: ${new Date(cacheInfo.last_updated).toLocaleTimeString()}`
                }
              </span>
            )}
          </div>
        </div>
        <div className="news-grid">
          {articles.length === 0 ? (
            <p>No news found.</p>
          ) : (
            articles.map((a) => (
              <div key={a.url} className="news-card">
                <h2>{a.title}</h2>
                <p>{a.description}</p>
                <a href={a.url} target="_blank" rel="noreferrer">
                  Read more
                </a>
                <p className="news-meta">
                  Source: {a.source} | {new Date(a.publishedAt).toLocaleString()}
                </p>
                <button
                  onClick={() =>
                    navigate("/chat", {
                      state: {
                        id: a.url, 
                        text: a.content || a.description || a.title, 
                        title: a.title,
                      },
                    })
                  }
                >
                  Chat with this Article
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default NewsList;
