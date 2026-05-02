import React from 'react';

const ClusterStatus = ({ state }) => {
  if (!state) return <div className="text-[#869397]">Waiting for consensus...</div>;

  return (  
    <div className="bg-[#171d1e] p-6 rounded-xl border border-[#303638] shadow-lg h-full">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-[#dee3e6]">Live Cluster State</h2>
        <div className="flex gap-4">
          <span className="bg-[#0b2a36] text-[#4cd7f6] px-3 py-1 rounded-full text-sm">
            Term: {state.term}
          </span>
          <span className="bg-[#1b2122] text-[#dee3e6] border border-[#303638] px-3 py-1 rounded-full text-sm">
            Role: {state.role}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(state.nodes).map(([id, info]) => (
          <div key={id} className={`p-6 rounded-lg border-2 transition-all ${
            state.leader === id ? 'border-[#ffb873] bg-[#5b3200]/20' : 'border-[#303638] bg-[#1b2122]'
          }`}>
            <div className="flex justify-between items-start mb-4">
              <span className="text-2xl">🖥️</span>
              {state.leader === id && (
                <span className="text-[10px] bg-[#ffb873] text-black px-2 py-0.5 rounded font-bold uppercase">Leader</span>
              )}
            </div>
            <h3 className="font-bold text-lg mb-1 text-[#dee3e6]">{id}</h3>
            <p className={`text-sm ${info.alive ? 'text-[#4edea3]' : 'text-[#ffb4ab]'}`}>
              {info.alive ? '● Connected' : '○ Disconnected'}
            </p>
          </div>
        ))}
      </div>
      
      <div className="mt-8 p-4 bg-[#090f11] rounded border border-[#303638]">
         <h4 className="text-xs font-bold text-[#869397] uppercase mb-2">System Logs</h4>
         <p className="text-xs font-mono text-[#bcc9cd]">Current Leader: {state.leader || 'Electing...'}</p>
         <p className="text-xs font-mono text-[#bcc9cd]">Protocol: RaftOptima with Weighted Quorum</p>
      </div>
    </div>
  );
};

export default ClusterStatus;