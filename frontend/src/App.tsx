import "./index.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Memories from "./pages/Memories";
import Documents from "./pages/Documents";

/**
 * Root React component with routing setup.
 */
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/query" replace />} />
        <Route path="/query" element={<Memories />} />
        <Route path="/graph" element={<Memories />} />
        <Route path="/reasoning" element={<Memories />} />
        <Route path="/documents" element={<Documents />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
