import React, { useState } from 'react';

const ModAddForm = () => {
  const [activeTab, setActiveTab] = useState<'curseforge' | 'upload'>('curseforge');
  const [curseforgeUrl, setCurseforgeUrl] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  const handleCurseForgeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsAdding(true);
    
    // Simulate adding mod
    setTimeout(() => {
      setIsAdding(false);
      alert(`Mod added from: ${curseforgeUrl}`);
    }, 1500);
  };

  return (
    <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
      <div className="flex border-b border-gray-700 mb-6">
        <button
          className={`px-4 py-2 font-medium ${activeTab === 'curseforge' ? 'border-b-2 border-yellow-500 text-yellow-500' : 'text-gray-400'}`}
          onClick={() => setActiveTab('curseforge')}
        >
          From CurseForge
        </button>
        <button
          className={`px-4 py-2 font-medium ${activeTab === 'upload' ? 'border-b-2 border-yellow-500 text-yellow-500' : 'text-gray-400'}`}
          onClick={() => setActiveTab('upload')}
        >
          Upload .jar
        </button>
      </div>
      
      {activeTab === 'curseforge' ? (
        <form onSubmit={handleCurseForgeSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">CurseForge URL</label>
            <input
              type="text"
              value={curseforgeUrl}
              onChange={(e) => setCurseforgeUrl(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500"
              placeholder="https://www.curseforge.com/minecraft/mc-mods/modname"
              required
            />
          </div>
          <button
            type="submit"
            disabled={isAdding}
            className={`bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded transition ${
              isAdding ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {isAdding ? 'Adding...' : 'Add Mod'}
          </button>
        </form>
      ) : (
        <div>
          <p className="text-gray-300 mb-4">Upload a .jar file to add a custom mod</p>
          <div className="bg-gray-750 p-4 rounded-lg">
            <ModUploadForm />
          </div>
        </div>
      )}
      
      <div className="mt-6 bg-gray-750 p-4 rounded-lg">
        <h3 className="font-semibold mb-2">How it works</h3>
        <ul className="list-disc pl-5 text-sm text-gray-300 space-y-1">
          <li>CurseForge mods are automatically resolved and added to the server</li>
          <li>Custom .jar uploads are quarantined and scanned for viruses</li>
          <li>Role 2 users can approve uploads instantly</li>
          <li>Role 1 users must vote on new mods</li>
          <li>Updates are automatically checked every 30 minutes</li>
        </ul>
      </div>
    </div>
  );
};

export default ModAddForm;
