import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axiosConfig';
import { Form, Button, Card, Alert, Spinner, Row, Col } from 'react-bootstrap';

const MAX_N_SIZE_CLIENT = 5000;

const CreateTask = () => {
  const [name, setName] = useState(`Задача ${new Date().toLocaleString()}`);
  const [maxN, setMaxN] = useState(MAX_N_SIZE_CLIENT);
  const [inputType, setInputType] = useState('text');
  const [matrixText, setMatrixText] = useState('');
  const [file, setFile] = useState(null);

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [queueInfo, setQueueInfo] = useState(null);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
        if (selectedFile.size > 100 * 1024 * 1024) { 
            setError('Файл занадто великий (макс. 100MB).');
            setFile(null);
            e.target.value = null; 
        } else {
            setFile(selectedFile);
            setError(''); 
        }
    } else {
        setFile(null); 
    }
  };

  const validateInput = () => {
    setError(''); 
    if (inputType === 'text') {
        if (!matrixText.trim()) {
            setError('Поле вводу матриці не може бути порожнім.');
            return false;
        }
        const lines = matrixText.trim().split('\n');
        if (lines.length > maxN) {
            setError(`Перевищено ліміт на кількість невідомих. Введено ${lines.length}, а максимальна кількість ${maxN}.`);
            return false;
        }
    } else { 
        if (!file) {
            setError('Необхідно завантажити файл.');
            return false;
        }
    }
    if (isNaN(maxN) || maxN <= 0 || maxN > MAX_N_SIZE_CLIENT) {
        setError(`Некоректне значення для кількості невідомих. Має бути число від 1 до ${MAX_N_SIZE_CLIENT}.`);
        return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setQueueInfo(null); 
    if (!validateInput()) {
      return;
    }

    setLoading(true);

    const formData = new FormData();
    formData.append('name', name);
    formData.append('max_n', maxN);
    formData.append('save_matrices', false);

    if (inputType === 'text') {
      formData.append('matrix_text', matrixText);
    } else {
      formData.append('source_file', file);
    }

    try {
      const response = await api.post('/tasks/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const newTaskData = response.data;
      const newTaskId = newTaskData.id;

      if (newTaskData.status === 'queued') {
          setQueueInfo({
              message: newTaskData.queue_message || "Задача додана в чергу через завантаженість системи.",
              position: newTaskData.queue_position,
              waitTime: newTaskData.estimated_wait_time_sec,
              taskId: newTaskId
          });
          setTimeout(() => {
            navigate(`/task/${newTaskId}`);
          }, 5000); 
      } else {
          navigate(`/task/${newTaskId}`);
      }

    } catch (err) {
      console.error(err);
      let detailedError = '';
      if (err.response?.data) {
          const errors = err.response.data;
          detailedError = Object.entries(errors)
              .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`)
              .join('; ');
      }
      setError(detailedError || 'Помилка створення задачі.');
      setLoading(false);
    }
  };

  return (
    <Card>
      <Card.Header as="h2">Створити Нову Задачу</Card.Header>
      <Card.Body>
        {error && <Alert variant="danger" onClose={() => setError('')} dismissible>{error}</Alert>}
        {queueInfo && (
            <Alert variant="info">
                <Alert.Heading>Задача додана в чергу!</Alert.Heading>
                <p>{queueInfo.message}</p>
                {queueInfo.position && <p>Ваша позиція: {queueInfo.position}.</p>}
                {queueInfo.waitTime !== null && <p>Приблизний час очікування: {queueInfo.waitTime} секунд.</p>}
                <p>Вас буде перенаправлено на сторінку задачі за кілька секунд...</p>
                <Button variant="outline-info" size="sm" onClick={() => navigate(`/task/${queueInfo.taskId}`)}>
                      Перейти зараз
                </Button>
            </Alert>
        )}
        {!queueInfo && (
            <Form onSubmit={handleSubmit}>

            <Form.Group as={Row} className="mb-3" controlId="taskName">
                <Form.Label column sm={2}>Назва задачі</Form.Label>
                <Col sm={10}>
                <Form.Control
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                />
                </Col>
            </Form.Group>

            <Form.Group as={Row} className="mb-3" controlId="maxN">
                <Form.Label column sm={2}>Кількість невідомих (необов’язково)</Form.Label>
                <Col sm={10}>
                <Form.Control
                    type="number"
                    value={maxN}
                    onChange={(e) => setMaxN(parseInt(e.target.value) || 0)}
                    required
                    min="1" 
                    max={MAX_N_SIZE_CLIENT}
                />
                <Form.Text muted>
                    Обмеження на максимальну кількість невідомих — {MAX_N_SIZE_CLIENT}.
                </Form.Text>
                </Col>
            </Form.Group>

            <hr />
            <Form.Group className="mb-3">
                <Form.Label>Джерело даних</Form.Label>
                <div>
                    <Form.Check
                    inline
                    type="radio"
                    label="Ввести вручну"
                    name="inputType"
                    id="inputTypeText"
                    checked={inputType === 'text'}
                    onChange={() => { setInputType('text'); setFile(null); setError(''); }}
                    />
                    <Form.Check
                    inline
                    type="radio"
                    label="Завантажити .txt файл"
                    name="inputType"
                    id="inputTypeFile"
                    checked={inputType === 'file'}
                    onChange={() => { setInputType('file'); setMatrixText(''); setError(''); }} 
                    />
                </div>
            </Form.Group>

            {inputType === 'text' ? (
                <Form.Group controlId="matrixText" className="mb-3">
                <Form.Label>Матриця A та Вектор b</Form.Label>
                <Form.Control
                    as="textarea"
                    rows={10}
                    placeholder="Введіть матрицю. Кожен рядок - числа через пробіл. Останнє число в рядку - елемент вектора b."
                    value={matrixText}
                    onChange={(e) => setMatrixText(e.target.value)}
                    disabled={loading} 
                />
                </Form.Group>
            ) : (
                <Form.Group controlId="matrixFile" className="mb-3">
                <Form.Label>Файл (.txt)</Form.Label>
                <Form.Control
                    type="file"
                    accept=".txt, text/plain"
                    onChange={handleFileChange}
                    disabled={loading} 
                />
                {}
                {file && <Form.Text muted>Вибрано файл: {file.name}</Form.Text>}
                </Form.Group>
            )}

            <Button type="submit" variant="primary" disabled={loading} className="w-100 mt-3">
                {loading ? (
                <>
                    <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                    {' '}Створення...
                </>
                ) : (
                'Створити Задачу'
                )}
            </Button>
            </Form>
        )}
      </Card.Body>
    </Card>
  );
};

export default CreateTask;