import React, { useState } from 'react';

const ModUploadForm = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = () => {
    if (!file) {
      alert('Please select a file');
      return;
    }

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
  };

  return (
    <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
      <h2 className="text-xl font-semibold mb-4">Upload .jar File</h2>
      
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Select .jar File</label>
        <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center">
          <svg 
            className="w-12 h-12 mx-auto text-gray-400 mb-4" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24" 
            xmlns="http://www.w3.org/2000/svg"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M7 16a4 4 0 01-.88-7.583 5 5 0 119.769 2.456A7.5 7.5 0 0116 9.405 7.5 7.5 0 0112 16z"
            />
          </svg>
          <p className="mb-2">Drag & drop your .jar file here</p>
          <p className="text-sm text-gray-400 mb-4">or</p>
          <label className="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded cursor-pointer transition">
            Browse Files
            <input 
              type="file" 
              accept=".jar" 
              onChange={handleFileChange} 
              className="hidden" 
            />
          </label>
        </div>
        
        {file && (
          <p className="mt-2 text-sm text-gray-300">Selected: {file.name}</p>
        )}
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
      
      <button
        onClick={handleUpload}
        disabled={isUploading || !file}
        className={`mt-4 bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded transition ${
          isUploading || !file ? 'opacity-50 cursor-not-allowed' : ''
        }`}
      >
        {isUploading ? 'Uploading...' : 'Upload Mod'}
      </button>
      
      <div className="mt-6 bg-gray-750 p-4 rounded-lg">
        <h3 className="font-semibold mb-2">Upload Guidelines</h3>
        <ul className="list-disc pl-5 text-sm text-gray-300 space-y-1">
          <li>Only .jar files are accepted</li>
          <li>All uploads are scanned for viruses</li>
          <li>Role 2 users can approve uploads instantly</li>
          <li>Role 1 users must vote on new uploads</li>
          <li>Files are quarantined until approval</li>
        </ul>
      </div>
    </div>
  );
};

export default ModUploadForm;
