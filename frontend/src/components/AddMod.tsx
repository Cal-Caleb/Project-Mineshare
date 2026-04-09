import React, { useState } from 'react';

const AddMod = () => {
  const [activeTab, setActiveTab] = useState<'curseforge' | 'upload'>('curseforge');
  const [curseforgeUrl, setCurseforgeUrl] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleCurseForgeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Simulate adding mod from CurseForge
    alert(`Adding mod from: ${curseforgeUrl}`);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setIsUploading(true);
      setUploadProgress(0);
      
      // Simulate upload progress
      const interval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 100) {
            clearInterval(interval);
            setIsUploading(false);
            alert('Upload complete! Awaiting approval.');
            return 100;
          }
          return prev + 10;
        });
      }, 200);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Add New Mod</h1>
      
      <div className="flex border-b border-gray-700">
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
        <form onSubmit={handleCurseForgeSubmit} className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <div className="mb-4">
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
            className="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded transition"
          >
            Add Mod
          </button>
        </form>
      ) : (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Upload .jar File</label>
            <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center">
              <p className="mb-2">Drag & drop your .jar file here</p>
              <p className="text-sm text-gray-400 mb-4">or</p>
              <label className="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded cursor-pointer transition">
                Browse Files
                <input 
                  type="file" 
                  accept=".jar" 
                  onChange={handleFileUpload} 
                  className="hidden" 
                />
              </label>
            </div>
          </div>
          
          {isUploading && (
            <div className="mt-4">
              <div className="w-full bg-gray-700 rounded-full h-2.5">
                <div 
                  className="bg-yellow-600 h-2.5 rounded-full transition-all duration-300" 
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p className="text-center mt-2">{uploadProgress}% uploaded</p>
            </div>
          )}
        </div>
      )}
      
      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <h2 className="text-xl font-semibold mb-4">How it works</h2>
        <ul className="list-disc pl-5 space-y-2 text-gray-300">
          <li>CurseForge mods are automatically resolved and added to the server</li>
          <li>Custom .jar uploads are quarantined and scanned for viruses</li>
          <li>Role 2 users can approve uploads instantly</li>
          <li>Role 1 users must vote on new mods</li>
        </ul>
      </div>
    </div>
  );
};

export default AddMod;
