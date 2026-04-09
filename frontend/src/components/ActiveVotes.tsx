import React, { useState, useEffect } from 'react';

const ActiveVotes = () => {
  const [votes, setVotes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching votes
    const fetchVotes = () => {
      setTimeout(() => {
        setVotes([
          {
            id: 1,
            modName: "Sodium",
            type: "add",
            votes: { yes: 12, no: 3 },
            total: 15,
            status: "pending",
            timeLeft: "12h 30m"
          },
          {
            id: 2,
            modName: "OptiFine",
            type: "remove",
            votes: { yes: 2, no: 8 },
            total: 10,
            status: "pending",
            timeLeft: "6h 15m"
          }
        ]);
        setLoading(false);
      }, 500);
    };

    fetchVotes();
  }, []);

  const handleVote = (voteId: number, vote: boolean) => {
    // Simulate voting
    alert(`Voted ${vote ? 'yes' : 'no'} on vote ${voteId}`);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Active Votes</h1>
      
      {votes.length === 0 ? (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 text-center">
          <p className="text-gray-400">No active votes at the moment</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {votes.map((vote) => (
            <div key={vote.id} className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-semibold">{vote.modName}</h2>
                  <p className={`text-sm ${vote.type === 'add' ? 'text-green-400' : 'text-red-400'}`}>
                    {vote.type === 'add' ? 'Add Mod' : 'Remove Mod'}
                  </p>
                </div>
                <span className="bg-yellow-600 text-white text-xs px-2 py-1 rounded">
                  {vote.status}
                </span>
              </div>
              
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-1">
                  <span>Yes: {vote.votes.yes}</span>
                  <span>No: {vote.votes.no}</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2.5">
                  <div 
                    className="bg-green-600 h-2.5 rounded-full" 
                    style={{ width: `${(vote.votes.yes / vote.total) * 100}%` }}
                  ></div>
                </div>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Time left: {vote.timeLeft}</span>
                <div className="flex space-x-2">
                  <button 
                    onClick={() => handleVote(vote.id, true)}
                    className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm transition"
                  >
                    Yes
                  </button>
                  <button 
                    onClick={() => handleVote(vote.id, false)}
                    className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm transition"
                  >
                    No
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ActiveVotes;
