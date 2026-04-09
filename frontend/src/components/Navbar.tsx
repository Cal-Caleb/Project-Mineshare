import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navbar = () => {
  const location = useLocation();

  return (
    <nav className="bg-gray-800 border-b border-gray-700">
      <div className="container mx-auto px-4 py-3 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-yellow-500 rounded-full flex items-center justify-center animate-float">
            <span className="text-black font-bold text-lg">M</span>
          </div>
          <span className="text-xl font-bold">ModServer</span>
        </div>
        
        <div className="flex space-x-6">
          <Link 
            to="/" 
            className={`hover:text-yellow-400 transition ${location.pathname === '/' ? 'text-yellow-400' : ''}`}
          >
            Dashboard
          </Link>
          <Link 
            to="/mods" 
            className={`hover:text-yellow-400 transition ${location.pathname === '/mods' ? 'text-yellow-400' : ''}`}
          >
            Mods
          </Link>
          <Link 
            to="/add-mod" 
            className={`hover:text-yellow-400 transition ${location.pathname === '/add-mod' ? 'text-yellow-400' : ''}`}
          >
            Add Mod
          </Link>
          <Link 
            to="/votes" 
            className={`hover:text-yellow-400 transition ${location.pathname === '/votes' ? 'text-yellow-400' : ''}`}
          >
            Votes
          </Link>
          <Link 
            to="/audit" 
            className={`hover:text-yellow-400 transition ${location.pathname === '/audit' ? 'text-yellow-400' : ''}`}
          >
            Audit
          </Link>
          <Link 
            to="/admin" 
            className={`hover:text-yellow-400 transition ${location.pathname === '/admin' ? 'text-yellow-400' : ''}`}
          >
            Admin
          </Link>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
