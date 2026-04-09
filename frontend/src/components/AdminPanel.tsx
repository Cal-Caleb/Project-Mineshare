import React, { useState } from 'react';

const AdminPanel = () => {
  const [modName, setModName] = useState('');
  const [forceAction, setForceAction] = useState<'add' | 'remove'>('add');

  const handleForceAction = () => {
    if (!modName) {
      alert('Please enter a mod name');
      return;
    }
    
    if (forceAction === 'add') {
      alert(`Force adding mod: ${modName}`);
    } else {
      alert(`Force removing mod: ${modName}`);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Admin Panel</h1>
      
      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <h2 className="text-xl font-semibold mb-4">Force Add/Remove Mod</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Mod Name</label>
            <input
              type="text"
              value={modName}
              onChange={(e) => setModName(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500"
              placeholder="Enter mod name"
            />
          </div>
          
          <div className="flex space-x-4">
            <button
              onClick={() => setForceAction('add')}
              className={`px-4 py-2 rounded ${forceAction === 'add' ? 'bg-green-600' : 'bg-gray-700'}`}
            >
              Add
            </button>
            <button
              onClick={() => setForceAction('remove')}
              className={`px-4 py-2 rounded ${forceAction === 'remove' ? 'bg-red-600' : 'bg-gray-700'}`}
            >
              Remove
            </button>
          </div>
          
          <button
            onClick={handleForceAction}
            className="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded transition"
          >
            Execute Force Action
          </button>
        </div>
      </div>
      
      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <h2 className="text-xl font-semibold mb-4">Server Management</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button className="bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded transition">
            Manual Update Check
          </button>
          <button className="bg-purple-600 hover:bg-purple-700 text-white py-3 px-4 rounded transition">
            Restart Server
          </button>
          <button className="bg-orange-600 hover:bg-orange-700 text-white py-3 px-4 rounded transition">
            Backup World
          </button>
          <button className="bg-red-600 hover:bg-red-700 text-white py-3 px-4 rounded transition">
            Rollback Last Update
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
