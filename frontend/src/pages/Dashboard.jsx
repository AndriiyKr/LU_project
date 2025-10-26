import React, { useState, useEffect } from 'react';
import { } from 'react-router-dom';
import api from '../api/axiosConfig';
import { Table, Button, Alert } from 'react-bootstrap';
import { LinkContainer } from 'react-router-bootstrap';
import TaskStatusBadge from '../components/TaskStatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';

const Dashboard = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        setLoading(true);
        setError('');
        const response = await api.get('/tasks/');
        setTasks(response.data);
      } catch (err) {
        setError('Не вдалося завантажити список задач.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchTasks();
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert variant="danger">{error}</Alert>;

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h1>Ваші Задачі</h1>
        <LinkContainer to="/create-task">
          <Button variant="primary">Створити Нову Задачу</Button>
        </LinkContainer>
      </div>
      
      {tasks.length === 0 ? (
        <Alert variant="info">У вас ще немає жодної задачі.</Alert>
      ) : (
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th>ID</th>
              <th>Назва</th>
              <th>Статус</th>
              <th>Створено</th>
              <th>Завершено</th>
              <th>Дії</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.id}>
                <td>{task.id}</td>
                <td>{task.name}</td>
                <td>
                  <TaskStatusBadge status={task.status} />
                </td>
                <td>{new Date(task.created_at).toLocaleString()}</td>
                <td>{task.completed_at ? new Date(task.completed_at).toLocaleString() : '---'}</td>
                <td>
                  <LinkContainer to={`/task/${task.id}`}>
                    <Button variant="info" size="sm">
                      Деталі
                    </Button>
                  </LinkContainer>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
};

export default Dashboard;