import React, { useState, useEffect } from 'react';
import { Activity, Box, Server, Skull, Terminal, Play, AlertTriangle } from 'lucide-react';
import Overview from './components/Overview';
import Chaos from './components/Chaos';
import Telemetry from './components/Telemetry';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [clusterState, setClusterState] = useState(null);
  const [nodeContainers, setNodeContainers] = useState({});
  const [logs, setLogs] = useState([]);

  // HARDCODED PORTS FOR YOUR PYTHON BACKEND
  const CONTROL_PLANE_URL = "http://127.0.0.1:5001";
  const WORKER_PORTS = [5001, 5002, 5003];

  const addLog = (msg, type = "info") => {
    setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev].slice(0, 15));
  };

  useEffect(() => {
    const fetchState = async () => {
      try {
        const cpRes = await fetch(`${CONTROL_PLANE_URL}/cluster_state`);
        const cpData = await cpRes.json();
        setClusterState(cpData);

        let containers = {};
        for (const port of WORKER_PORTS) {
          try {
            const res = await fetch(`http://127.0.0.1:${port}/containers`);
            const data = await res.json();
            containers[`node${port - 5000}`] = data;
          } catch (e) {
            containers[`node${port - 5000}`] = [];
          }
        }
        setNodeContainers(containers);
      } catch (error) {
        // Prevent spamming the logs if the backend is off
        if (logs.length === 0 || !logs[0].includes("Connection lost")) {
          addLog(`Connection to Control Plane lost...`, "error");
        }
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 2000);
    return () => clearInterval(interval);
  }, []);

  if (!clusterState) return <div className="flex h-screen items-center justify-center text-[#869397] bg-[#0e1416] font-mono text-sm tracking-widest uppercase">Waiting for Control Plane connection...</div>;

  return (
    <div className="min-h-screen bg-[#0e1416] text-[#dee3e6] p-6 font-sans">
      
      {/* GLOBAL HEADER */}
      <header className="flex justify-between items-center mb-8 border-b border-[#303638] pb-4">
        <div className="flex items-center gap-4">
          <Box className="w-8 h-8 text-[#4cd7f6]" />
          <h1 className="text-2xl font-bold tracking-tight text-white uppercase tracking-tighter">MiniOrch_V1</h1>
          <div className="flex items-center gap-2 px-3 py-1 bg-[#004e5c]/30 text-[#4cd7f6] text-xs rounded border border-[#00687a]/50 font-mono ml-4">
            <span className="opacity-70">TERM:</span> {clusterState.term} 
            <span className="mx-2 opacity-30">|</span> 
            <span className="opacity-70">LEADER:</span> {clusterState.leader || "ELECTING..."}
          </div>
        </div>
        
        {/* TAB NAVIGATION */}
        <div className="flex gap-2 bg-[#1b2122] p-1 rounded border border-[#303638]">
          <button onClick={() => setActiveTab('overview')} className={`px-4 py-2 rounded-sm text-sm font-medium transition-colors ${activeTab === 'overview' ? 'bg-[#00687a] text-white' : 'text-[#869397] hover:text-white'}`}>
            Overview
          </button>
          <button onClick={() => setActiveTab('chaos')} className={`px-4 py-2 rounded-sm text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'chaos' ? 'bg-[#93000a] text-[#ffdad6]' : 'text-[#869397] hover:text-white'}`}>
            <Skull className="w-4 h-4"/> Chaos Studio
          </button>
          <button onClick={() => setActiveTab('hood')} className={`px-4 py-2 rounded-sm text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'hood' ? 'bg-[#5b3200] text-[#ffdcbf]' : 'text-[#869397] hover:text-white'}`}>
            <Terminal className="w-4 h-4"/> Telemetry
          </button>
        </div>
      </header>

      {/* RENDER ACTIVE SCREEN */}
      <main>
        {activeTab === 'overview' && <Overview clusterState={clusterState} nodeContainers={nodeContainers} logs={logs} addLog={addLog} />}
        {activeTab === 'chaos' && <Chaos nodeContainers={nodeContainers} addLog={addLog} />}
        {activeTab === 'hood' && <Telemetry clusterState={clusterState} nodeContainers={nodeContainers} />}
      </main>

    </div>
  );
}