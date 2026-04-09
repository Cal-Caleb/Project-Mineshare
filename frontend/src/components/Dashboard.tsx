import React, { useState, useEffect } from 'react';

const Dashboard = () => {
  const [serverStatus, setServerStatus] = useState<string>('unknown');
  const [playersOnline, setPlayersOnline] = useState<number>(0);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  useEffect(() => {
    // Simulate fetching server status
    const fetchStatus = () => {
      setServerStatus('online');
      setPlayersOnline(12);
      setLastUpdate('2023-05-15 14:30:00');
    };
    
    fetchStatus();
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Server Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-xl font-semibold mb-2">Server Status</h2>
          <p className={`text-lg ${serverStatus === 'online' ? 'text-green-400' : 'text-red-400'}`}>
            {serverStatus.charAt(0).toUpperCase() + serverStatus.slice(1)}
          </p>
        </div>
        
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-xl font-semibold mb-2">Players Online</h2>
          <p className="text-2xl font-bold">{playersOnline}</p>
        </div>
        
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-xl font-semibold mb-2">Last Update</h2>
          <p>{lastUpdate}</p>
        </div>
      </div>
      
      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
        <div className="space-y-3">
          <div className="flex justify-between items-center border-b border-gray-700 pb-2">
            <span>Mod added: OptiFine</span>
            <span className="text-gray-400">5 minutes ago</span>
          </div>
          <div className="flex justify-between items-center border-b border-gray-700 pb-2">
            <span>Vote started: Sodium</span>
            <span className="text-gray-400">1 hour ago</span>
          </div>
          <div className="flex justify-between items-center border-b border-gray-700 pb-2">
            <span>Server restarted</span>
            <span className="text-gray-400">2 hours ago</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
