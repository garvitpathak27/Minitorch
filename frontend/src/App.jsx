import React, { useState, useEffect } from 'react';
import axios from 'axios';
import NodeControls from './components/NodeControls';
import DeployWorkload from './components/DeployWorkload';
import Overview from './components/Overview';
import Telemetry from './components/Telemetry';
import Chaos from './components/Chaos';

const MANAGER_URL = "http://127.0.0.1:8000";
const RAFT_NODE_URL = "http://127.0.0.1:5001"; 

function App() {
  const [procStatus, setProcStatus] = useState({});
  const [clusterState, setClusterState] = useState({ nodes: {}, term: 0, leader: null, role: 'follower' });
  const [nodeContainers, setNodeContainers] = useState({});
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');

  const addLog = (msg, type = "info") => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [`[${timestamp}] ${type.toUpperCase()}: ${msg}`, ...prev].slice(0, 50));
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        // 1. Get process status (Running/Stopped) from manager.py
        const procRes = await axios.get(`${MANAGER_URL}/status`);
        setProcStatus(procRes.data);

        // 2. Get Raft state from node1
        const raftRes = await axios.get(`${RAFT_NODE_URL}/cluster_state`);
        setClusterState(raftRes.data);

        // 3. Fetch container data from each node's local API
        const containerData = {};
        for (const nodeId of ['node1', 'node2', 'node3']) {
          const port = 5000 + parseInt(nodeId.replace('node', ''));
          try {
            const cRes = await axios.get(`http://127.0.0.1:${port}/containers`, { timeout: 500 });
            containerData[nodeId] = cRes.data;
          } catch {
            containerData[nodeId] = [];
          }
        }
        setNodeContainers(containerData);
      } catch (err) {
        // Silence errors if nodes are simply offline
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#090f11] text-[#dee3e6] font-sans">
      <nav className="bg-[#111827] border-b border-[#303638] px-8 py-4 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-mono font-bold text-[#4cd7f6] tracking-tighter">MINITORCH_v2</h1>
          <div className="flex gap-2">
            {['overview', 'telemetry', 'chaos'].map(tab => (
              <button 
                key={tab} 
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1 text-xs font-mono uppercase tracking-widest rounded-sm transition-all ${activeTab === tab ? 'bg-[#4cd7f6] text-black' : 'hover:bg-[#303638]'}`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-right">
            <p className="text-[10px] text-[#869397] uppercase">Raft Term</p>
            <p className="font-mono text-[#ffb873]">{clusterState.term}</p>
          </div>
          <div className="text-right border-l border-[#303638] pl-6">
            <p className="text-[10px] text-[#869397] uppercase">Leader</p>
            <p className="font-mono text-[#4edea3]">{clusterState.leader || 'ELECTING...'}</p>
          </div>
        </div>
      </nav>

      <main className="p-8">
        {activeTab === 'overview' && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
              <div className="space-y-8">
                <NodeControls procStatus={procStatus} managerUrl={MANAGER_URL} clusterState={clusterState} />
                <DeployWorkload raftUrl={RAFT_NODE_URL} />
              </div>
              <div className="lg:col-span-3">
                <Overview 
                  clusterState={clusterState} 
                  nodeContainers={nodeContainers} 
                  logs={logs} 
                  addLog={addLog} 
                />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'telemetry' && (
          <Telemetry clusterState={clusterState} nodeContainers={nodeContainers} />
        )}

        {activeTab === 'chaos' && (
          <Chaos nodeContainers={nodeContainers} addLog={addLog} />
        )}
      </main>
    </div>
  );
}

export default App;