import React, { useState } from 'react';
import axios from 'axios';

const DeployWorkload = ({ raftUrl }) => {
  const [img, setImg] = useState("");
  const [status, setStatus] = useState({ type: null, message: "" });

  const handleDeploy = async () => {
    if (!img) return;
    try {
      setStatus({ type: null, message: "" });
      // Wrapper "command" required by transport.py
      const payload = {
        command: {
          action: "create_workload",
          id: `workload-${Date.now()}`,
          image_path: img,
          replicas: 1,
          command: ["/bin/sleep", "3600"]
        }
      };
      await axios.post(`${raftUrl}/submit`, payload);
      setStatus({ type: "success", message: "Command submitted to Raft." });
      setImg("");
    } catch (err) {
      setStatus({ type: "error", message: "Only the leader can accept deployments." });
    }
  };

  return (
    <div className="bg-[#171d1e] p-6 rounded-xl border border-[#303638] shadow-lg">
      <h2 className="text-xl font-semibold mb-4 text-[#dee3e6]">🚀 Deploy Container</h2>
      <label className="block text-[10px] font-mono uppercase tracking-widest text-[#869397] mb-2">
        Image Path (local filesystem)
      </label>
      <input 
        type="text" 
        placeholder="e.g. nginx:latest or /tmp/ubuntu" 
        className="w-full p-2 mb-4 bg-[#090f11] border border-[#303638] rounded text-[#dee3e6] focus:outline-none focus:border-[#4cd7f6]"
        value={img}
        onChange={(e) => setImg(e.target.value)}
      />
      {status.type && (
        <div
          className={`mb-4 px-3 py-2 rounded border text-xs font-mono uppercase tracking-widest ${
            status.type === "success"
              ? 'bg-[#0b2b1f] border-[#4edea3] text-[#4edea3]'
              : 'bg-[#2b0f12] border-[#ffb4ab] text-[#ffb4ab]'
          }`}
        >
          {status.message}
        </div>
      )}
      <button 
        onClick={handleDeploy}
        className="w-full bg-[#4edea3] hover:bg-[#3dbd84] py-2 rounded font-bold transition-colors text-black"
      >
        Submit to Cluster
      </button>
    </div>
  );
};

export default DeployWorkload;