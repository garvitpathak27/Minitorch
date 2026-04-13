import requests
import time 
import threading

def heartbeat_loop(node_id: str , control_plane_url: str):
    while True:
        try:
            requests.post(
                f"{control_plane_url}/nodes/heartbeat",
                json={
                    "id" : node_id
                }
            )
            print(f"heartbeat sent {node_id}" )

        except Exception as e:
            print(f"heatbeat failed : {e}")
        
        time.sleep(5)

def start_heartbeat(node_id: str, control_plane_url: str):
    # start heartbeat_loop in a background thread
    # daemon=True means this thread dies when the main process dies
    t = threading.Thread(
        target=heartbeat_loop,
        args=(node_id, control_plane_url),
        daemon=True
    )
    t.start()
    print(f"heartbeat started for node {node_id}")