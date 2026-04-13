import { useState, useEffect } from 'react'

function App() {
  const [nodes, setNodes] = useState([])
  const [workloads, setWorkloads] = useState([])
  
  // Form state
  const [imagePath, setImagePath] = useState('/tmp/testroot')
  const [command, setCommand] = useState('sleep 30')
  const [replicas, setReplicas] = useState(1)

  // Poll the backend every 2 seconds
  useEffect(() => {
    const fetchData = async () => {
      try {
        const nodesRes = await fetch('http://localhost:6001/nodes')
        const nodesData = await nodesRes.json()
        setNodes(nodesData)

        const wlRes = await fetch('http://localhost:6001/workloads')
        const wlData = await wlRes.json()
        setWorkloads(wlData)
      } catch (err) {
        console.error("Failed to fetch data. Is the control plane running?")
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 2000)
    return () => clearInterval(interval)
  }, [])

  const submitWorkload = async (e) => {
    e.preventDefault()
    await fetch('http://localhost:6001/workloads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_path: imagePath,
        command: command.split(' '),
        replicas: parseInt(replicas)
      })
    })
  }

  // Helper to check if node is dead (no heartbeat for 30s)
  const isNodeAlive = (lastSeen) => {
    const now = Date.now() / 1000 // Convert JS ms to Python seconds
    return (now - lastSeen) < 30
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'system-ui' }}>
      <h1>MiniOrch Dashboard</h1>
      
      <div style={{ display: 'flex', gap: '20px' }}>
        
        {/* LEFT COLUMN: Submit Workloads */}
        <div style={{ flex: 1, padding: '20px', border: '1px solid #ccc' }}>
          <h2>Deploy Workload</h2>
          <form onSubmit={submitWorkload} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <label>
              Image: <input value={imagePath} onChange={e => setImagePath(e.target.value)} />
            </label>
            <label>
              Command: <input value={command} onChange={e => setCommand(e.target.value)} />
            </label>
            <label>
              Replicas: <input type="number" value={replicas} onChange={e => setReplicas(e.target.value)} min="1" />
            </label>
            <button type="submit" style={{ padding: '10px', background: '#007bff', color: 'white', border: 'none' }}>
              Deploy
            </button>
          </form>
        </div>

        {/* MIDDLE COLUMN: Desired State */}
        <div style={{ flex: 1, padding: '20px', border: '1px solid #ccc' }}>
          <h2>Workloads (Desired State)</h2>
          {workloads.map(wl => {
            // Count how many containers are actually running for this workload across all nodes
            const actual = nodes.reduce((total, node) => {
              return total + node.containers.filter(c => c.startsWith(wl.id)).length
            }, 0)

            return (
              <div key={wl.id} style={{ marginBottom: '10px', padding: '10px', background: '#f8f9fa' }}>
                <strong>ID:</strong> {wl.id} <br/>
                <strong>Status:</strong> {actual} / {wl.replicas} Replicas Running
              </div>
            )
          })}
        </div>

        {/* RIGHT COLUMN: Actual State (Nodes) */}
        <div style={{ flex: 2, padding: '20px', border: '1px solid #ccc' }}>
          <h2>Cluster Nodes (Actual State)</h2>
          {nodes.map(node => {
            const alive = isNodeAlive(node.last_seen)
            return (
              <div key={node.id} style={{ marginBottom: '15px', padding: '10px', borderLeft: `5px solid ${alive ? 'green' : 'red'}` }}>
                <strong>{node.id}</strong> ({node.address}) - 
                <span style={{ color: alive ? 'green' : 'red', marginLeft: '10px' }}>
                  {alive ? 'HEALTHY' : 'DEAD'}
                </span>
                
                <div style={{ marginTop: '10px' }}>
                  <strong>Containers:</strong>
                  {node.containers.length === 0 ? ' None' : (
                    <ul>
                      {node.containers.map(c => <li key={c}>{c}</li>)}
                    </ul>
                  )}
                </div>
              </div>
            )
          })}
        </div>

      </div>
    </div>
  )
}

export default App