import React, { useState, useEffect } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import ModCatalogue from './components/ModCatalogue';
import AddMod from './components/AddMod';
import ActiveVotes from './components/ActiveVotes';
import AuditHistory from './components/AuditHistory';
import AdminPanel from './components/AdminPanel';
import Navbar from './components/Navbar';
import Starfield from './components/Starfield';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

function App() {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-yellow-500 mx-auto mb-4"></div>
          <p className="text-xl">Loading ModServer...</p>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <div className="min-h-screen bg-gray-900 text-white relative overflow-hidden">
        <Starfield />
        <div className="relative z-10">
          <Navbar />
          <div className="container mx-auto px-4 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/mods" element={<ModCatalogue />} />
              <Route path="/add-mod" element={<AddMod />} />
              <Route path="/votes" element={<ActiveVotes />} />
              <Route path="/audit" element={<AuditHistory />} />
              <Route path="/admin" element={<AdminPanel />} />
            </Routes>
          </div>
        </div>
      </div>
    </Router>
  );
}

export default App;
