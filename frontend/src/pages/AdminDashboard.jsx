import React, { useState, useEffect } from 'react';
import api from '../api/axiosConfig';
import { Card, Col, Row, Alert, Spinner, Table, Button, Badge } from 'react-bootstrap';
import LoadingSpinner from '../components/LoadingSpinner';
import { LinkContainer } from 'react-router-bootstrap';
import TaskStatusBadge from '../components/TaskStatusBadge';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const AdminTaskList = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response = await api.get('/monitoring/all-tasks/');
      setTasks(response.data);
    } catch (err) {
      setError('Не вдалося завантажити список всіх задач.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const handleCancelTask = async (taskId) => {
    if (!window.confirm(`Ви впевнені, що хочете скасувати задачу ID: ${taskId}?`)) {
      return;
    }
    try {
      await api.post(`/tasks/${taskId}/cancel/`);
      fetchTasks();
    } catch (err) {
      alert('Помилка скасування задачі.');
    }
  };

  if (loading) return <LoadingSpinner text="Завантаження всіх задач..." />;
  if (error) return <Alert variant="danger">{error}</Alert>;

  return (
    <Card>
      <Card.Header as="h3">Всі Задачі в Системі</Card.Header>
      <Card.Body>
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th>ID</th>
              <th>Власник</th>
              <th>Назва</th>
              <th>Статус</th>
              <th>Створено</th>
              <th>Дії</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.id}>
                <td>{task.id}</td>
                <td><Badge bg="secondary">{task.owner}</Badge></td>
                <td>{task.name}</td>
                <td><TaskStatusBadge status={task.status} /></td>
                <td>{new Date(task.created_at).toLocaleString()}</td>
                <td>
                  <LinkContainer to={`/task/${task.id}`}>
                    <Button variant="info" size="sm" className="me-2">
                      Деталі
                    </Button>
                  </LinkContainer>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleCancelTask(task.id)}
                    disabled={['completed', 'failed', 'cancelled'].includes(task.status)}
                  >
                    Скасувати
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card.Body>
    </Card>
  );
};

const chartOptions = {
  responsive: true,
  scales: { y: { beginAtZero: true, max: 100 } },
  plugins: { legend: { display: false } },
};

const AdminDashboard = () => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [cpuHistory, setCpuHistory] = useState([]);
  const [ramHistory, setRamHistory] = useState([]);
  const [currentHostname, setCurrentHostname] = useState(''); 

  const fetchMetrics = async () => {
    try {
      const response = await api.get('/monitoring/metrics/');
      const newMetrics = response.data;
      setMetrics(newMetrics);

      const now = new Date().toLocaleTimeString();

      setCpuHistory(prev => [...prev.slice(-20), { x: now, y: newMetrics.system.cpu_percent }]);
      setRamHistory(prev => [...prev.slice(-20), { x: now, y: newMetrics.system.ram_percent }]);
      setCurrentHostname(newMetrics.system.hostname); 
      setError(''); 
    } catch (err) {
      setError('Не вдалося завантажити метрики.');
      console.error(err);
    } finally {
      setLoading(false); 
    }
  };

  useEffect(() => {
    fetchMetrics(); 
    const interval = setInterval(fetchMetrics, 1000); 
    return () => clearInterval(interval);
  }, []);

  if (loading && !metrics) return <LoadingSpinner text="Завантаження метрик..." />;
  if (error && !metrics) return <Alert variant="danger">{error}</Alert>;
  if (!metrics) return null;


  const { system, tasks, users, workers } = metrics;
  const cpuChartData = {
    labels: cpuHistory.map(d => d.x),
    datasets: [{
      label: 'CPU %',
      data: cpuHistory.map(d => d.y),
      borderColor: 'rgb(53, 162, 235)',
      backgroundColor: 'rgba(53, 162, 235, 0.5)',
    }],
  };

  const ramChartData = {
    labels: ramHistory.map(d => d.x),
    datasets: [{
      label: 'RAM %',
      data: ramHistory.map(d => d.y),
      borderColor: 'rgb(255, 99, 132)',
      backgroundColor: 'rgba(255, 99, 132, 0.5)',
    }],
  };

  return (
    <div>
      <h1 className="mb-4">Панель Адміністратора</h1>
      {error && <Alert variant="warning">Помилка оновлення метрик: {error}</Alert>}
      {loading && <Spinner animation="border" size="sm" className="mb-2 ms-2" />}
      <h3 className="mt-4">
        Навантаження Сервера (Live) <Badge bg="info"></Badge>
      </h3>
      <Row>
        <Col md={6}>
          <Card className="mb-3">
            <Card.Body>
              <Card.Title>Навантаження CPU</Card.Title>
              <h4 className="display-6">{system.cpu_percent.toFixed(1)}%</h4>
              <Line options={chartOptions} data={cpuChartData} />
            </Card.Body>
          </Card>
        </Col>
        <Col md={6}>
          <Card className="mb-3">
            <Card.Body>
              <Card.Title>Використання RAM</Card.Title>
              <h4 className="display-6">{system.ram_percent.toFixed(1)}%</h4>
              <small>{system.ram_used_mb.toFixed(0)} MB / {system.ram_total_mb.toFixed(0)} MB</small>
              <Line options={chartOptions} data={ramChartData} />
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <h3 className="mt-4">Задачі та Користувачі</h3>
      <Row>
        <Col md={3}>
          <Card bg="primary" text="white" className="mb-3">
            <Card.Body>
              <Card.Title>Активні Задачі</Card.Title>
              <h2 className="display-4">{tasks.active_tasks}</h2>
              (В черзі + Виконуються)
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card bg="info" text="dark" className="mb-3">
            <Card.Body>
              <Card.Title>Воркери (Celery)</Card.Title>
              <h2 className="display-4">{workers.count}</h2>
              (з {workers.max_replicas} макс.)
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card bg="success" text="white" className="mb-3">
            <Card.Body>
              <Card.Title>Виконано (24г)</Card.Title>
              <h2 className="display-4">{tasks.completed_last_24h}</h2>
              завдань
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card bg="dark" text="white" className="mb-3">
            <Card.Body>
              <Card.Title>Аккаунтів</Card.Title>
              <h2 className="display-4">{users.total_users}</h2>
              користувачів
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <AdminTaskList />
    </div>
  );
};

export default AdminDashboard;