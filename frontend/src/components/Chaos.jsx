// src/components/Chaos.jsx
import React from 'react';
import { Skull, Server } from 'lucide-react';

export default function Chaos({ nodeContainers, addLog }) {
  const killContainer = async (nodeId, containerId) => {
    const port = 5000 + parseInt(nodeId.replace('node', ''));
    addLog(`CHAOS: Assassinating container ${containerId} on ${nodeId}`, "warn");
    try {
      await fetch(`http://127.0.0.1:${port}/containers/${containerId}`, { method: 'DELETE' });
    } catch(e) {
      addLog(`Failed to reach ${nodeId} API`, "error");
    }
  };

  return (
    <div className="flex-grow flex justify-center w-full py-2">
      <div className="max-w-5xl w-full flex flex-col gap-6">
        
        {/* Header: DangerHeader */}
        <div className="bg-[#93000a]/20 border border-[#ffb4ab] p-6 rounded flex items-start gap-4">
          <div className="bg-[#93000a] text-[#ffb4ab] p-3 rounded flex-shrink-0">
            <Skull className="w-8 h-8" />
          </div>
          <div>
            <h1 className="font-mono text-2xl font-bold text-[#ffb4ab] uppercase mb-1">Chaos Studio</h1>
            <p className="font-sans text-sm text-[#bcc9cd]">
              Violently destroy infrastructure components to test system resilience and automated failover capabilities. Use with extreme caution in production environments.
            </p>
          </div>
        </div>

        {/* Section A: Assassination Grid */}
        <section className="flex flex-col gap-4">
          <div className="border-b border-[#303638] pb-1">
            <h2 className="font-mono text-[13px] text-[#bcc9cd] uppercase tracking-widest">Assassination Grid (Target Namespaces)</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.keys(nodeContainers).map(nodeId => 
              nodeContainers[nodeId].map(c => (
                <button 
                  key={c.id}
                  onClick={() => killContainer(nodeId, c.id)}
                  className="group bg-[#0e1416] border border-[#3d494c] rounded p-3 flex justify-between items-center hover:border-[#ffb4ab] hover:bg-[#93000a]/10 transition-colors cursor-crosshair text-left"
                >
                  <div className="flex flex-col gap-1">
                    <span className="font-mono text-[13px] text-[#dee3e6] group-hover:text-[#ffb4ab] transition-colors uppercase">
                      KILL {c.id}
                    </span>
                    <span className="font-mono text-[11px] text-[#bcc9cd]">Host: {nodeId} | PID: {c.pid}</span>
                  </div>
                  <div className="text-[#bcc9cd] group-hover:text-[#ffb4ab] transition-colors p-1">
                    <Skull className="w-5 h-5" />
                  </div>
                </button>
              ))
            )}
          </div>
          
          {Object.values(nodeContainers).every(arr => arr.length === 0) && (
            <div className="text-center py-12 border border-dashed border-[#3d494c] text-[#bcc9cd] font-mono text-sm">
              No active containers available to assassinate.
            </div>
          )}
        </section>

        {/* Section B: Node Crash Simulator */}
        <section className="mt-6">
          <div className="bg-[#e89337]/20 border border-[#e89337] rounded p-6">
            <div className="flex items-center gap-3 mb-4 border-b border-[#e89337]/30 pb-3">
              <Server className="w-6 h-6 text-[#ffb873]" />
              <h2 className="font-sans text-lg font-semibold text-[#ffb873]">Total Node Failure Test</h2>
            </div>
            <div className="font-mono text-[13px] text-[#ffb873]/80 space-y-1">
              <p>&gt; WARNING: Initiating this test will simulate an ungraceful shutdown of the underlying hardware.</p>
              <p>&gt; To trigger catastrophic failure simulation on a specific node:</p>
              <p className="pl-4 text-[#ffb873]">&gt; ssh root@nodeX</p>
              <p className="pl-4 text-[#ffb873]">&gt; echo c &gt; /proc/sysrq-trigger</p>
              <p>&gt; Or press CTRL+C in the backend terminal to abort the Python process.</p>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}