import React from 'react';
import { Activity, Play, Server, ShieldAlert } from 'lucide-react';

export default function Overview({ clusterState, nodeContainers, logs, addLog }) {
  
  const deployWorkload = async () => {
    addLog("Initiating Ubuntu deployment (2 Replicas)...", "info");
    try {
      await fetch(`http://127.0.0.1:5001/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: { action: "create_workload", id: "ubuntu-sleep", image_path: "/tmp/ubuntu", replicas: 2, command: ["/bin/sleep", "3600"] }
        })
      });
    } catch (e) {
      addLog("Failed to contact leader node.", "error");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      
      {/* LEFT COLUMN: COMMAND & CONTROL */}
      <div className="lg:col-span-1 space-y-6">
        
        {/* Deploy Card */}
        <div className="bg-[#171d1e] border border-[#303638] p-5">
          <div className="flex items-center gap-2 mb-4">
            <Play className="w-5 h-5 text-[#4edea3]" />
            <h2 className="text-lg font-semibold text-[#dee3e6]">Quick Deploy</h2>
          </div>
          <button onClick={deployWorkload} className="w-full py-3 bg-[#00a572] hover:bg-[#4edea3] text-[#00311f] font-bold tracking-widest text-xs uppercase transition-colors rounded-sm">
            Deploy Workload
          </button>
        </div>

        {/* Terminal Log */}
        <div className="bg-[#090f11] border border-[#303638] flex flex-col h-[500px]">
          <div className="bg-[#1b2122] px-3 py-2 flex items-center justify-between border-b border-[#303638]">
            <span className="font-mono text-[10px] text-[#869397]">CONSOLE_OUTPUT</span>
            <div className="flex gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[#ffb4ab]/40"></div>
              <div className="w-2 h-2 rounded-full bg-[#ffb873]/40"></div>
              <div className="w-2 h-2 rounded-full bg-[#4edea3]/40"></div>
            </div>
          </div>
          <div className="overflow-y-auto p-4 font-mono text-[11px] leading-loose space-y-1">
            {logs.map((log, i) => (
              <div key={i} className={`${log.includes('error') || log.includes('CHAOS') ? 'text-[#ffb4ab]' : 'text-[#bcc9cd]'}`}>
                {log}
              </div>
            ))}
            {logs.length === 0 && <div className="text-[#869397] italic">Awaiting events...</div>}
            <div className="animate-pulse inline-block w-2 h-3 bg-[#4cd7f6] translate-y-0.5 mt-2"></div>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: THE NODE MAP */}
      <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-6">
        {Object.keys(clusterState.nodes).map(nodeId => {
          const isAlive = clusterState.nodes[nodeId].alive;
          const containers = nodeContainers[nodeId] || [];
          
          return (
            <div key={nodeId} className={`bg-[#171d1e] border transition-all duration-300 relative ${isAlive ? 'border-[#303638]' : 'border-[#93000a]/50 opacity-60'}`}>
              
              {/* Dead Node Overlay */}
              {!isAlive && <div className="absolute inset-0 bg-[#93000a]/5 pointer-events-none z-10"></div>}

              {/* Node Header */}
              <div className={`p-4 border-b flex justify-between items-start ${isAlive ? 'border-[#303638]' : 'border-[#93000a]/30'}`}>
                <div>
                  <h3 className={`font-mono text-lg ${isAlive ? 'text-[#4cd7f6]' : 'text-[#ffb4ab]'}`}>{nodeId}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <div className={`w-2 h-2 rounded-full ${isAlive ? 'bg-[#4edea3] animate-pulse-status' : 'bg-[#ffb4ab]'}`}></div>
                    <span className={`font-mono text-[9px] uppercase tracking-widest ${isAlive ? 'text-[#4edea3]' : 'text-[#ffb4ab]'}`}>
                      {isAlive ? 'Status: Alive' : 'Status: Dead'}
                    </span>
                  </div>
                </div>
                {nodeId === clusterState.leader && isAlive && (
                  <div className="bg-[#5b3200] text-[#ffb873] border border-[#ffb873]/30 px-2 py-1 font-mono text-[9px] flex items-center gap-1 uppercase tracking-widest">
                    Raft Leader
                  </div>
                )}
              </div>

              {/* Node Body (Containers) */}
              <div className="p-4 space-y-3 min-h-[200px]">
                {isAlive ? (
                  <>
                    <div className="font-mono text-[9px] text-[#869397] mb-3 uppercase tracking-widest">Active Namespaces ({containers.length})</div>
                    {containers.map(c => (
                      <div key={c.id} className="flex items-center justify-between p-3 bg-[#252b2d] border border-[#303638]">
                        <div className="flex flex-col">
                          <span className="font-mono text-[#4cd7f6] text-xs uppercase">{c.id}</span>
                          <span className="font-mono text-[10px] text-[#869397] mt-1">PID: {c.pid}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 bg-[#4edea3] rounded-full animate-pulse-status"></div>
                          <span className="font-mono text-[9px] text-[#4edea3] tracking-widest uppercase">{c.status}</span>
                        </div>
                      </div>
                    ))}
                  </>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center py-8">
                    <ShieldAlert className="text-[#ffb4ab]/50 w-8 h-8 mb-3" />
                    <p className="font-mono text-[9px] text-[#ffb4ab] uppercase tracking-widest">Connection Timeout</p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
}