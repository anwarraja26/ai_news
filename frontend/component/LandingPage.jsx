import React from "react";
import "./LandingPage.css";

const LandingPage = ({ onStart }) => {
  return (
    <div className="landing-container">
      <div className="landing-content">
        <h1 className="landing-quote">
          Chat With News that matters.<br />
          Right now!!!!
        </h1>
        <button className="start-button" onClick={onStart}>
          Let's Get Started
        </button>
      </div>
    </div>
  );
};

export default LandingPage;
