// frontend/src/hooks/useTaskWebSocket.js
import { useState, useEffect, useRef } from 'react';
import ReconnectingWebSocket from 'reconnecting-websocket';

// Цей хук керує WebSocket з'єднанням для однієї задачі
const useTaskWebSocket = (taskUuid) => {
  const [taskState, setTaskState] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    if (!taskUuid) return;

    // Визначаємо протокол (ws:// або wss:// для HTTPS)
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsHost = window.location.hostname;
    const wsUrl = `${protocol}://${wsHost}/ws/tasks/updates/${taskUuid}/`;

    // Використовуємо ReconnectingWebSocket для стабільності
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
      
      // Обробляємо початковий стан
      if (data.type === 'initial_state') {
        setTaskState({
          status: data.status,
          stage: data.stage,
          percentage: data.percentage,
          result_message: data.result_message,
        });
      }

      // Обробляємо оновлення
      if (data.type === 'update') {
        setTaskState({
          status: data.status,
          stage: data.stage,
          percentage: data.percentage,
          result_message: data.result_message,
        });

        // Додаємо лог, якщо він є
        if (data.log_message) {
          setLogs((prevLogs) => [
            ...prevLogs,
            `${new Date().toLocaleTimeString()}: ${data.log_message}`,
          ]);
        }
      }
    };

    // Закриваємо з'єднання при розмонтуванні компонента
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [taskUuid]);

  return { taskState, logs, isConnected };
};

export default useTaskWebSocket;