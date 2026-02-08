import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "../component/LandingPage";
import NewsList from "../component/NewsLists";
import ChatPage from "../component/ChatPage"; // 🔹 create this file

function App() {
  const [start, setStarted] = useState(false);

  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={
            !start ? (
              <LandingPage onStart={() => setStarted(true)} />
            ) : (
              <NewsList />
            )
          }
        />
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </Router>
  );
}

export default App;
