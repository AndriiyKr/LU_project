import { useState, useEffect, useRef } from 'react';
import ReconnectingWebSocket from 'reconnecting-websocket';

const useTaskWebSocket = (taskUuid) => {
  const [taskState, setTaskState] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    if (!taskUuid) return;

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsHost = window.location.hostname;
    const wsUrl = `${protocol}://${wsHost}/ws/tasks/updates/${taskUuid}/`;

    ws.current = new ReconnectingWebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log(`WebSocket connected for task ${taskUuid}`);
      setIsConnected(true);
    };

    ws.current.onclose = () => {
      console.log(`WebSocket disconnected for task ${taskUuid}`);
      setIsConnected(false);
    };

    ws.current.onerror = (err) => {
      console.error('WebSocket error:', err);
    };

    ws.current.onmessage = (e) => {
      const data = JSON.parse(e.data);
      
      if (data.type === 'initial_state') {
        setTaskState({
          status: data.status,
          stage: data.stage,
          percentage: data.percentage,
          result_message: data.result_message,
          matrix_size: data.matrix_size,
        });
      }

      if (data.type === 'update') {
        setTaskState({
          status: data.status,
          stage: data.stage,
          percentage: data.percentage,
          result_message: data.result_message,
          matrix_size: data.matrix_size,
        });

        if (data.log_message) {
          setLogs((prevLogs) => [
            ...prevLogs,
            `${new Date().toLocaleTimeString()}: ${data.log_message}`,
          ]);
        }
      }
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [taskUuid]);

  return { taskState, logs, isConnected };
};

export default useTaskWebSocket;