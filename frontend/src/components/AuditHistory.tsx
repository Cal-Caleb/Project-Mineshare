import React, { useState, useEffect } from 'react';

const AuditHistory = () => {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching audit events
    const fetchEvents = () => {
      setTimeout(() => {
        setEvents([
          {
            id: 1,
            timestamp: '2023-05-15 14:30:00',
            user: 'Player123',
            action: 'Added mod',
            details: 'OptiFine',
            source: 'web'
          },
          {
            id: 2,
            timestamp: '2023-05-15 13:45:00',
            user: 'AdminUser',
            action: 'Voted on mod',
            details: 'Sodium - Yes',
            source: 'discord'
          },
          {
            id: 3,
            timestamp: '2023-05-15 12:00:00',
            user: 'Player456',
            action: 'Requested mod',
            details: 'Phantom',
            source: 'web'
          },
          {
            id: 4,
            timestamp: '2023-05-14 20:15:00',
            user: 'AdminUser',
            action: 'Server restarted',
            details: 'Automatic update',
            source: 'bot'
          }
        ]);
        setLoading(false);
      }, 500);
    };

    fetchEvents();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Audit History</h1>
      
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-750">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Timestamp</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">User</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Action</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Details</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Source</th>
            </tr>
          </thead>
          <tbody className="bg-gray-800 divide-y divide-gray-700">
            {events.map((event) => (
              <tr key={event.id} className="hover:bg-gray-750">
                <td className="px-6 py-4 whitespace-nowrap text-sm">{event.timestamp}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{event.user}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{event.action}</td>
                <td className="px-6 py-4 text-sm">{event.details}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    event.source === 'web' ? 'bg-blue-900 text-blue-300' : 
                    event.source === 'discord' ? 'bg-purple-900 text-purple-300' : 
                    'bg-green-900 text-green-300'
                  }`}>
                    {event.source}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AuditHistory;
