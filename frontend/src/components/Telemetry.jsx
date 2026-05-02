// src/components/Telemetry.jsx
import React from 'react';

export default function Telemetry({ clusterState, nodeContainers }) {
  
  // Lightweight JSON syntax highlighter to achieve the "Terminal" aesthetic
  const syntaxHighlight = (jsonObj) => {
    if (!jsonObj) return '';
    let json = JSON.stringify(jsonObj, null, 2);
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    const highlighted = json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
      let colorClass = 'text-[#4edea3]'; // String: Neon Green
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          // JSON Key: Cyan
          const key = match.replace(/:$/, '');
          return `<span class="text-[#06b6d4]">${key}</span><span class="text-[#869397]">:</span>`;
        }
      } else if (/true|false/.test(match)) {
        colorClass = 'text-[#ffb873]'; // Boolean: Yellow
      } else if (/null/.test(match)) {
        colorClass = 'text-[#ffb4ab]'; // Null: Red
      } else {
        colorClass = 'text-[#e89337]'; // Number: Orange
      }
      return `<span class="${colorClass}">${match}</span>`;
    });

    // Colorize curly braces and brackets (Punctuation: Outline/Gray)
    return highlighted.replace(/([\{\}\[\]])/g, '<span class="text-[#869397]">$1</span>');
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-140px)]">
      
      {/* RAFT STATE PANEL (Left) */}
      <div className="flex flex-col h-full rounded border border-[#3d494c] overflow-hidden bg-black shadow-lg">
        {/* Chrome Header */}
        <div className="bg-[#111827] border-b border-[#3d494c] px-4 py-3 flex items-center justify-between shrink-0">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-[#ffb4ab]"></div>
            <div className="w-3 h-3 rounded-full bg-[#e89337]"></div>
            <div className="w-3 h-3 rounded-full bg-[#4edea3]"></div>
          </div>
          <div className="font-mono text-[11px] text-[#bcc9cd] font-medium tracking-widest uppercase">
            Raft_ControlPlane_State.json
          </div>
          <div className="w-12"></div> {/* Spacer for balance */}
        </div>
        
        {/* Terminal Content */}
        <div className="flex-1 p-5 overflow-y-auto font-mono text-[13px] leading-relaxed whitespace-pre">
          <code 
            dangerouslySetInnerHTML={{ __html: syntaxHighlight(clusterState) }} 
          />
        </div>
      </div>

      {/* CGROUP TELEMETRY PANEL (Right) */}
      <div className="flex flex-col h-full rounded border border-[#3d494c] overflow-hidden bg-black shadow-lg">
        {/* Chrome Header */}
        <div className="bg-[#111827] border-b border-[#3d494c] px-4 py-3 flex items-center justify-between shrink-0">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-[#ffb4ab]"></div>
            <div className="w-3 h-3 rounded-full bg-[#e89337]"></div>
            <div className="w-3 h-3 rounded-full bg-[#4edea3]"></div>
          </div>
          <div className="font-mono text-[11px] text-[#bcc9cd] font-medium tracking-widest uppercase">
            Linux_CGroup_Telemetry.json
          </div>
          <div className="w-12"></div> {/* Spacer for balance */}
        </div>
        
        {/* Terminal Content */}
        <div className="flex-1 p-5 overflow-y-auto font-mono text-[13px] leading-relaxed whitespace-pre">
          <code 
            dangerouslySetInnerHTML={{ __html: syntaxHighlight(nodeContainers) }} 
          />
        </div>
      </div>

    </div>
  );
}