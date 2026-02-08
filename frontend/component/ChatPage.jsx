import React, { useState, useRef, useEffect } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import "./ChatPage.css";

const ChatPage = () => {
  const location = useLocation();
  const { id, text, title } = location.state || {};

  const [messages, setMessages] = useState([
    { sender: "system", text: ` Chatting with: ${title}` },
  ]);
  const [input, setInput] = useState("");
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);

    // Store the current input value before clearing
    const currentInput = input;

    // Clear input immediately
    setInput(""); 

    try {
      const res = await axios.post("http://localhost:8000/chat", {
        article_id: id,
        article_text: text,
        question: currentInput, // Use stored input value
      });

      const botMessage = { 
        sender: "bot", 
        text: res.data.answer
      };
      setMessages((prev) => [...prev, botMessage]);
      
      // Focus back to input after sending
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 100);
      
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Error fetching response" },
      ]);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="chat-container">
      <div className="chat-header">Chat with Article</div>

      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.sender}`}>
            <p>{m.text}</p>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      <div className="chat-input">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me anything..."
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage}> ➤ </button>
      </div>
    </div>
  );
};

export default ChatPage;
