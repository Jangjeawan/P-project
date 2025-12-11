import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Analysis from "./pages/Analysis";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 메인 홈 */}
        <Route path="/" element={<Home />} />

        {/* Auth */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* Dashboard */}
        <Route path="/dashboard" element={<Dashboard />} />
        
        <Route path="/analysis" element={<Analysis />} />

      
      </Routes>
    </BrowserRouter>
  );
}

export default App;