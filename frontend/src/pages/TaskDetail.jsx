// frontend/src/pages/TaskDetail.jsx
import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/axiosConfig';
import useTaskWebSocket from '../hooks/useTaskWebSocket'; // (Пункт 2)
import { Card, Row, Col, Alert, Button, ProgressBar, Spinner, ListGroup, Badge } from 'react-bootstrap';
import LoadingSpinner from '../components/LoadingSpinner';
import TaskStatusBadge from '../components/TaskStatusBadge';

const TaskDetail = () => {
  const { id } = useParams();
  // --- Зміни стану ---
  const [initialTaskData, setInitialTaskData] = useState(null); // Дані, завантажені через HTTP
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [isCancelling, setIsCancelling] = useState(false);

  // --- 1. HTTP Fetch для початкових/статичних даних ---
  useEffect(() => {
    const fetchTask = async () => {
      try {
        setLoading(true);
        setError('');
        const response = await api.get(`/tasks/${id}/`);
        setInitialTaskData(response.data); // Зберігаємо початкові дані
        console.log("Initial task data loaded:", response.data);
      } catch (err) {
        setError('Не вдалося завантажити задачу. Можливо, вона не існує або у вас немає доступу.');
        console.error("Fetch task error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchTask();
  }, [id]);

  // --- 2. WebSocket для Real-time оновлень ---
  // Хук отримує ТІЛЬКИ ДИНАМІЧНІ дані: { status, stage, percentage, log_message, result_message }
  const { taskState, logs, isConnected } = useTaskWebSocket(initialTaskData?.uuid);

  // --- ВИДАЛЕНО НЕПОТРІБНИЙ useEffect для злиття станів ---
  // Ми будемо використовувати initialTaskData та taskState окремо у рендері

  // --- 3. Функції-дії (без змін) ---
  const handleCancelTask = async () => {
    // ... (код без змін) ...
    setActionError('');
    setIsCancelling(true);
    try {
      await api.post(`/tasks/${id}/cancel/`);
      // Статус оновиться автоматично через WebSocket
    } catch (err) {
      setActionError(err.response?.data?.error || 'Помилка скасування.');
      console.error("Cancel task error:", err);
    } finally {
      setIsCancelling(false);
    }
  };

  const handleDownloadResult = () => {
    // ... (код без змін) ...
     api.get(`/tasks/${id}/download/`, {
        responseType: 'blob',
    })
    .then(response => {
        // ... (код створення посилання) ...
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `result_task_${id}.txt`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url); // Очистка
    })
    .catch(err => {
        console.error("Download error", err);
        // Спробуємо прочитати JSON помилку з blob
        if (err.response && err.response.data instanceof Blob) {
            err.response.data.text().then(text => {
                 try {
                     const errorJson = JSON.parse(text);
                     setActionError(errorJson.detail || "Помилка завантаження файлу.");
                 } catch (parseError) {
                     setActionError("Помилка завантаження файлу (не вдалося розібрати відповідь).");
                 }
            });
        } else {
             setActionError(err.response?.data?.detail || "Помилка завантаження файлу.");
        }
    });
  };

  // --- Рендер ---
  if (loading) return <LoadingSpinner />;
  if (error) return <Alert variant="danger">{error} <Link to="/">На головну</Link></Alert>;
  if (!initialTaskData) return null; // Якщо початкові дані не завантажились

  // --- Логіка відображення ---
  // Беремо динамічні дані з WebSocket (taskState), якщо вони є,
  // інакше беремо з початкових даних (initialTaskData) або ставимо дефолтні.
  const currentStatus = taskState?.status || initialTaskData.status;
  const currentStage = taskState?.stage || initialTaskData.last_progress?.stage || (currentStatus === 'pending' ? 'Очікування парсингу' : '...');
  const currentProgress = taskState?.percentage ?? (initialTaskData.last_progress?.percentage ?? 0); // Використовуємо ?? для 0
  const resultMessage = taskState?.result_message || initialTaskData.result_message;

  const isRunning = currentStatus === 'running';
  const isQueued = currentStatus === 'queued';
  // const isPending = currentStatus === 'pending'; // Не використовується, можна видалити
  const isDone = ['completed', 'failed', 'cancelled'].includes(currentStatus);

  // Отримуємо статичні дані з initialTaskData
  const { name, uuid, created_at, started_at, completed_at, matrix_size, queue_position, estimated_wait_time_sec } = initialTaskData;

  return (
    <Row>
      {/* Головна інформація */}
      <Col md={7}>
        <Card>
          <Card.Header className="d-flex justify-content-between align-items-center">
            {/* Використовуємо name з initialTaskData */}
            <h3>{name} (ID: {id})</h3>
            {/* Використовуємо currentStatus */}
            <TaskStatusBadge status={currentStatus} />
          </Card.Header>
          <Card.Body>
            {/* Використовуємо uuid, created_at і т.д. з initialTaskData */}
            <p><strong>UUID:</strong> {uuid}</p>
            <p><strong>Створено:</strong> {new Date(created_at).toLocaleString()}</p>
            {started_at && <p><strong>Розпочато:</strong> {new Date(started_at).toLocaleString()}</p>}
            {completed_at && <p><strong>Завершено:</strong> {new Date(completed_at).toLocaleString()}</p>}
            <p><strong>Розмір матриці:</strong> {matrix_size ? `${matrix_size}x${matrix_size}` : 'N/A'}</p>

            {/* Інформація про чергу */}
            {/* Використовуємо isQueued та дані з initialTaskData */}
            {isQueued && (
              <Alert variant="info">
                <Alert.Heading>Задача у черзі</Alert.Heading>
                <p>
                  Ваша задача очікує на вільний воркер.
                  <br />
                  <strong>Позиція у черзі:</strong> {queue_position || '...'}
                  <br />
                  <strong>Приблизний час очікування:</strong> {estimated_wait_time_sec ? `${estimated_wait_time_sec} сек.` : 'Розрахунок...'}
                </p>
              </Alert>
            )}

            {/* Прогрес */}
            <hr />
            <h5>Прогрес Виконання</h5>
             {/* Використовуємо currentStage та currentProgress */}
            <p className="mb-1">{currentStage}</p>
            <ProgressBar
              animated={isRunning}
              now={currentProgress}
              label={`${currentProgress.toFixed(0)}%`}
              variant={currentStatus === 'failed' ? 'danger' : (currentStatus === 'completed' ? 'success' : 'primary')} // Додано variant='success'
            />

            {/* Повідомлення про результат/помилку */}
            {/* Використовуємо resultMessage */}
            {resultMessage && (
              <Alert variant={currentStatus === 'failed' ? 'danger' : 'success'} className="mt-3">
                <strong>Результат:</strong> {resultMessage}
              </Alert>
            )}

          </Card.Body>
          <Card.Footer className="d-flex justify-content-between">
            {/* Кнопки використовують isDone та currentStatus */}
            <div>
              <Button
                variant="danger"
                onClick={handleCancelTask}
                disabled={isDone || isCancelling}
                className="me-2"
              >
                {isCancelling ? <Spinner as="span" size="sm" /> : 'Скасувати Задачу'}
              </Button>
            </div>
            <div>
              <Button
                variant="success"
                onClick={handleDownloadResult}
                disabled={currentStatus !== 'completed'}
              >
                Завантажити Результат
              </Button>
            </div>
          </Card.Footer>
        </Card>
      </Col>

      {/* Логи та WS статус (без змін) */}
      <Col md={5}>
        <Card>
          <Card.Header>
             Логи (Live)
             <Badge bg={isConnected ? 'success' : 'danger'} className="float-end">
                {isConnected ? 'LIVE' : 'Connecting...'}
             </Badge>
          </Card.Header>
          <ListGroup variant="flush" style={{ height: '400px', overflowY: 'auto' }}>
            {/* Додаємо перевірку, чи initialTaskData.logs існує */}
            {(logs.length === 0 && (!initialTaskData.logs || initialTaskData.logs.length === 0)) && <ListGroup.Item>Очікування логів...</ListGroup.Item>}
            {/* Можна додати відображення старих логів з initialTaskData.logs, якщо потрібно */}
            {logs.map((log, index) => (
              <ListGroup.Item key={index} style={{ fontSize: '0.85rem', padding: '0.25rem 0.75rem' }}>
                <code>{log}</code>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Card>
        {actionError && <Alert variant="danger" className="mt-3">{actionError}</Alert>}
      </Col>
    </Row>
  );
};

export default TaskDetail;