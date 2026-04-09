import React, { useState, useEffect } from 'react';

const ModCatalogue = () => {
  const [mods, setMods] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching mods
    const fetchMods = () => {
      setTimeout(() => {
        setMods([
          {
            id: 1,
            name: "Sodium",
            status: "active",
            version: "0.4.1",
            author: "JellySquid",
            downloads: 125000,
            lastUpdate: "2023-05-10"
          },
          {
            id: 2,
            name: "OptiFine",
            status: "active",
            version: "1.19.4 HD U H6",
            author: "sp614x",
            downloads: 850000,
            lastUpdate: "2023-05-12"
          },
          {
            id: 3,
            name: "Phantom",
            status: "pending",
            version: "1.0.0",
            author: "Player123",
            downloads: 1200,
            lastUpdate: "2023-05-14"
          },
          {
            id: 4,
            name: "Lithium",
            status: "active",
            version: "0.11.1",
            author: "JellySquid",
            downloads: 450000,
            lastUpdate: "2023-05-05"
          }
        ]);
        setLoading(false);
      }, 500);
    };

    fetchMods();
  }, []);

  const filteredMods = mods.filter(mod => 
    mod.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    mod.author.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Mod Catalogue</h1>
      
      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Available Mods</h2>
          <div className="relative">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded px-4 py-2 pl-10 focus:outline-none focus:ring-2 focus:ring-yellow-500"
              placeholder="Search mods..."
            />
            <svg 
              className="w-5 h-5 absolute left-3 top-2.5 text-gray-400" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24" 
              xmlns="http://www.w3.org/2000/svg"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredMods.map((mod) => (
            <div key={mod.id} className="bg-gray-750 p-4 rounded-lg border border-gray-700 hover:border-yellow-500 transition">
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-lg font-semibold">{mod.name}</h3>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  mod.status === 'active' ? 'bg-green-900 text-green-300' : 'bg-yellow-900 text-yellow-300'
                }`}>
                  {mod.status}
                </span>
              </div>
              
              <p className="text-sm text-gray-400 mb-2">by {mod.author}</p>
              
              <div className="flex justify-between text-sm mb-3">
                <span>Version: {mod.version}</span>
                <span>{mod.downloads.toLocaleString()} downloads</span>
              </div>
              
              <div className="flex justify-between text-xs text-gray-500">
                <span>Last updated: {mod.lastUpdate}</span>
                <button className="text-yellow-500 hover:text-yellow-400 transition">
                  View Details
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ModCatalogue;
