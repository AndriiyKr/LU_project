import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/axiosConfig';
import useTaskWebSocket from '../hooks/useTaskWebSocket';
import { Card, Row, Col, Alert, Button, ProgressBar, Spinner, ListGroup, Badge } from 'react-bootstrap';
import LoadingSpinner from '../components/LoadingSpinner';
import TaskStatusBadge from '../components/TaskStatusBadge';

const TaskDetail = () => {
  const { id } = useParams();
  const [initialTaskData, setInitialTaskData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [isCancelling, setIsCancelling] = useState(false);

  useEffect(() => {
    const fetchTask = async () => {
      try {
            setLoading(true);
            setError('');
            const response = await api.get(`/tasks/${id}/`);
            setInitialTaskData(response.data);
            console.log("Initial task data loaded:", response.data);
        } catch (err) {
            if (err.response && err.response.status === 404) {
                setError(`Задача з ID ${id} не знайдена або у вас немає до неї доступу.`);
            } else {
                setError('Не вдалося завантажити задачу. Спробуйте оновити сторінку.');
            }
            console.error("Fetch task error:", err);
        } finally {
            setLoading(false);
        }
    };
    fetchTask();
  }, [id]);

  const { taskState, logs, isConnected } = useTaskWebSocket(initialTaskData?.uuid);

  const handleCancelTask = async () => {
        setActionError('');
        setIsCancelling(true);
        try {
            await api.post(`/tasks/${id}/cancel/`);
        } catch (err) {
            setActionError(err.response?.data?.error || 'Помилка скасування.');
            console.error("Cancel task error:", err);
        } finally {
            setIsCancelling(false);
        }
    };

    const handleDownloadResult = () => {
        api.get(`/tasks/${id}/download/`, {
            responseType: 'blob',
        })
        .then(response => {
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            const contentDisposition = response.headers['content-disposition'];
            let filename = `result_task_${id}.txt`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
                if (filenameMatch && filenameMatch.length > 1) {
                    filename = filenameMatch[1];
                }
            }
            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            setActionError(''); 
        })
        .catch(err => {
            console.error("Download error", err);
            if (err.response && err.response.data instanceof Blob && err.response.data.type === "application/json") {
                err.response.data.text().then(text => {
                    try {
                        const errorJson = JSON.parse(text);
                        setActionError(errorJson.detail || "Помилка завантаження файлу (сервер).");
                    } catch (parseError) {
                        setActionError("Помилка завантаження файлу (не вдалося розібрати відповідь сервера).");
                    }
                });
            } else if (err.response && err.response.data && typeof err.response.data.detail === 'string') {
                  setActionError(err.response.data.detail);
            } else {
                setActionError("Помилка завантаження файлу. Можливо, він ще не готовий.");
            }
        });
    };

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert variant="danger">{error} <Link to="/">На головну</Link></Alert>;
  if (!initialTaskData) return null;

  const currentStatus = taskState?.status || initialTaskData.status;
  const currentStage = taskState?.stage || initialTaskData.last_progress?.stage || (currentStatus === 'pending' ? 'Очікування парсингу' : '...');
  const currentProgress = taskState?.percentage ?? (initialTaskData.last_progress?.percentage ?? (currentStatus === 'completed' ? 100 : 0)); // Показуємо 100% для completed
  const resultMessage = taskState?.result_message || initialTaskData.result_message;
  const currentQueuePosition = taskState?.queue_position ?? initialTaskData.queue_position;
  const currentEstimatedWaitTime = taskState?.estimated_wait_time_sec ?? initialTaskData.estimated_wait_time_sec;


  const isRunning = currentStatus === 'running';
  const isQueuedOrPending = currentStatus === 'queued' || currentStatus === 'pending';
  const isDone = ['completed', 'failed', 'cancelled'].includes(currentStatus);

  const { name, uuid, created_at, started_at, completed_at, matrix_size } = initialTaskData;

  const formatWaitTime = (seconds) => {
      if (seconds === null || seconds === undefined) return 'Розрахунок...';
      if (seconds <= 0) return 'скоро';
      if (seconds < 60) return `~ ${seconds} сек.`;
      const minutes = Math.ceil(seconds / 60);
      return `~ ${minutes} хв.`;
  };

  return (
    <Row>
      {}
      <Col md={7}>
        <Card>
          <Card.Header className="d-flex justify-content-between align-items-center">
            <h3>{name} (ID: {id})</h3>
            <TaskStatusBadge status={currentStatus} />
          </Card.Header>
          <Card.Body>
            <p><strong>UUID:</strong> {uuid}</p>
            <p><strong>Створено:</strong> {new Date(created_at).toLocaleString()}</p>
            {started_at && <p><strong>Розпочато:</strong> {new Date(started_at).toLocaleString()}</p>}
            {completed_at && <p><strong>Завершено:</strong> {new Date(completed_at).toLocaleString()}</p>}
            <p><strong>Розмір матриці:</strong> {matrix_size ? `${matrix_size}x${matrix_size}` : 'N/A'}</p>
            {}
            {isQueuedOrPending && (
              <Alert variant="info" className="mt-3">
                <Alert.Heading>
                    {currentStatus === 'pending' ? 'Задача очікує обробки' : 'Задача у черзі'}
                </Alert.Heading>
                <p>
                  {currentStatus === 'pending'
                    ? 'Триває підготовка даних перед додаванням до основної черги обчислень.'
                    : 'Ваша задача очікує на вільний обчислювальний ресурс.'}
                  <br />
                  {}
                  {currentQueuePosition !== null && currentQueuePosition > 0 && (
                      <>
                        <strong>Позиція у черзі:</strong> {currentQueuePosition}
                        <br />
                      </>
                  )}
                  <strong>Приблизний час очікування до старту:</strong> {formatWaitTime(currentEstimatedWaitTime)}
                </p>
              </Alert>
            )}
            {}
            <hr />
            <h5>Прогрес Виконання</h5>
            <p className="mb-1">{currentStage}</p>
            <ProgressBar
              animated={isRunning}
              now={currentProgress}
              label={`${currentProgress.toFixed(0)}%`}
              variant={currentStatus === 'failed' ? 'danger' : (currentStatus === 'completed' ? 'success' : 'primary')}
            />

            {}
            {resultMessage && (
              <Alert variant={currentStatus === 'failed' || currentStatus === 'cancelled' ? 'danger' : 'success'} className="mt-3">
                <strong>{currentStatus === 'failed' ? 'Помилка' : (currentStatus === 'cancelled' ? 'Скасовано' : 'Результат')}:</strong> {resultMessage}
              </Alert>
            )}

          </Card.Body>
          <Card.Footer className="d-flex justify-content-between">
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

      {}
      <Col md={5}>
        <Card>
          <Card.Header>
            Етапи виконання:
            <Badge bg={isConnected ? 'success' : 'danger'} className="float-end ms-2">
                {isConnected ? 'LIVE' : 'Connecting...'}
            </Badge>
          </Card.Header>
          <ListGroup variant="flush" style={{ maxHeight: '400px', overflowY: 'auto', fontSize: '0.8rem' }}>
            {}
            {initialTaskData?.logs?.map((log, index) => (
              <ListGroup.Item key={`initial-${index}`} className="py-1 px-2 text-muted">
                  <small>{new Date(log.timestamp).toLocaleTimeString()}: {log.message}</small>
              </ListGroup.Item>
            ))}
            {}
            {logs.map((log, index) => (
              <ListGroup.Item key={`ws-${index}`} className="py-1 px-2">
                <code>{log}</code>
              </ListGroup.Item>
            ))}
            {(logs.length === 0 && (!initialTaskData.logs || initialTaskData.logs.length === 0)) && <ListGroup.Item className="py-1 px-2 text-muted">Очікування відповіді...</ListGroup.Item>}
          </ListGroup>
        </Card>
        {actionError && <Alert variant="danger" className="mt-3" onClose={() => setActionError('')} dismissible>{actionError}</Alert>}
      </Col>
    </Row>
  );
};

export default TaskDetail;