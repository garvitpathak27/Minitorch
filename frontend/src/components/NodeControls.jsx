import React from 'react';
import axios from 'axios';

const NodeControls = ({ procStatus, managerUrl, clusterState }) => {
  const toggleNode = async (nodeId, isRunning) => {
    const action = isRunning ? 'stop_node' : 'start_node';
    try {
      await axios.post(`${managerUrl}/${action}/${nodeId}`);
    } catch (err) {
      alert(`Failed to ${action} ${nodeId}`);
    }
  };

  return (
    <div className="bg-[#171d1e] p-6 rounded-xl border border-[#303638] shadow-lg">
      <h2 className="text-xl font-semibold mb-4 flex items-center text-[#dee3e6]">
        <span className="mr-2">⚙️</span> Node Management
      </h2>
      <div className="space-y-4">
        {['node1', 'node2', 'node3'].map((id) => {
          const isAlive = Boolean(clusterState?.nodes?.[id]?.alive);
          const isRunning = procStatus[id] === 'running' || isAlive;
          const statusLabel = isRunning ? 'running' : (procStatus[id] || 'offline');

          return (
            <div key={id} className="flex items-center justify-between p-3 bg-[#1b2122] rounded-lg border border-[#303638]">
              <div>
                <span className="font-mono text-sm uppercase text-[#dee3e6]">{id}</span>
                <div className="flex items-center mt-1">
                  <div className={`h-2 w-2 rounded-full mr-2 ${isRunning ? 'bg-[#4edea3] animate-pulse-status' : 'bg-[#ffb4ab]'}`} />
                  <span className="text-xs text-[#869397]">{statusLabel}</span>
                </div>
              </div>
              <button
                onClick={() => toggleNode(id, isRunning)}
                className={`px-4 py-1 rounded text-sm font-medium transition-colors ${
                  isRunning
                  ? 'bg-[#ffb4ab] hover:bg-[#ff9a8f] text-black'
                  : 'bg-[#4edea3] hover:bg-[#3dbd84] text-black'
                }`}
              >
                {isRunning ? 'Stop' : 'Start'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default NodeControls;