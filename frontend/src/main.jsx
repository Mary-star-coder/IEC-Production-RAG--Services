
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

// Find the root HTML element where the React application will be mounted.
ReactDOM.createRoot(document.getElementById("root")).render(
  // StrictMode helps identify potential problems during development.
  <React.StrictMode>
    {/* Enable client-side navigation using React Router. */}
    <BrowserRouter>
      {/* Render the main application component and its child pages. */}
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
