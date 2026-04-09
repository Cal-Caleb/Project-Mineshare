import React from 'react';

interface ModCardProps {
  name: string;
  status: 'active' | 'pending' | 'removed';
  version: string;
  author: string;
  downloads: number;
  lastUpdate: string;
  onAction?: () => void;
}

const ModCard: React.FC<ModCardProps> = ({ 
  name, 
  status, 
  version, 
  author, 
  downloads, 
  lastUpdate,
  onAction 
}) => {
  const statusColor = status === 'active' ? 'bg-green-900 text-green-300' : 
                     status === 'pending' ? 'bg-yellow-900 text-yellow-300' : 
                     'bg-red-900 text-red-300';

  return (
    <div className="bg-gray-750 p-4 rounded-lg border border-gray-700 hover:border-yellow-500 transition hover:shadow-lg">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold">{name}</h3>
        <span className={`px-2 py-1 text-xs rounded-full ${statusColor}`}>
          {status}
        </span>
      </div>
      
      <p className="text-sm text-gray-400 mb-2">by {author}</p>
      
      <div className="flex justify-between text-sm mb-3">
        <span>Version: {version}</span>
        <span>{downloads.toLocaleString()} downloads</span>
      </div>
      
      <div className="flex justify-between text-xs text-gray-500 mb-3">
        <span>Last updated: {lastUpdate}</span>
        <button 
          onClick={onAction}
          className="text-yellow-500 hover:text-yellow-400 transition"
        >
          View Details
        </button>
      </div>
      
      <div className="flex space-x-2">
        <button className="flex-1 bg-green-600 hover:bg-green-700 text-white py-1 px-2 rounded text-sm transition">
          Vote
        </button>
        <button className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-1 px-2 rounded text-sm transition">
          Details
        </button>
      </div>
    </div>
  );
};

export default ModCard;
