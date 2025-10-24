// frontend/src/pages/CreateTask.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axiosConfig';
import { Form, Button, Card, Alert, Spinner, Row, Col } from 'react-bootstrap';

const MAX_N_SIZE_CLIENT = 5000; // (Пункт 1)

const CreateTask = () => {
  const [name, setName] = useState(`Задача ${new Date().toLocaleString()}`);
  const [maxN, setMaxN] = useState(MAX_N_SIZE_CLIENT);
  const [inputType, setInputType] = useState('text'); // 'text' або 'file'
  const [matrixText, setMatrixText] = useState('');
  const [file, setFile] = useState(null);
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      // Перевірка розміру файлу (напр. 50MB)
      if (selectedFile.size > 100 * 1024 * 1024) {
        setError('Файл занадто великий (макс. 100MB).');
        setFile(null);
      } else {
        setFile(selectedFile);
        setError('');
      }
    }
  };

  // (Пункт 1) Перевірка на клієнті
  const validateInput = () => {
    if (inputType === 'text') {
      if (!matrixText.trim()) {
        setError('Поле вводу матриці не може бути порожнім.');
        return false;
      }
      // Проста перевірка на кількість рядків
      const lines = matrixText.trim().split('\n');
      if (lines.length > maxN) {
         setError(`Перевищено ліміт на кількість невідомих. Введено ${lines.length}, макс. ${maxN}.`);
         return false;
      }
    } else {
      if (!file) {
        setError('Необхідно завантажити файл.');
        return false;
      }
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!validateInput()) {
      return;
    }

    setLoading(true);

    // FormData використовується для відправки файлів
    const formData = new FormData();
    formData.append('name', name);
    formData.append('max_n', maxN);
    formData.append('save_matrices', false); // Можна додати чекбокс

    if (inputType === 'text') {
      formData.append('matrix_text', matrixText);
    } else {
      formData.append('source_file', file);
    }

    try {
      // POST /api/tasks/
      const response = await api.post('/tasks/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      // Після успішного створення, переходимо на сторінку задачі
      const newTaskId = response.data.id;
      navigate(`/task/${newTaskId}`);

    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.response?.data?.non_field_errors?.[0] || 'Помилка створення задачі.');
      setLoading(false);
    }
  };

  return (
    <Card>
      <Card.Header as="h2">Створити Нову Задачу</Card.Header>
      <Card.Body>
        {error && <Alert variant="danger">{error}</Alert>}
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
            <Form.Label column sm={2}>Макс. N</Form.Label>
            <Col sm={10}>
              <Form.Control
                type="number"
                value={maxN}
                onChange={(e) => setMaxN(parseInt(e.target.value))}
                required
                max={MAX_N_SIZE_CLIENT}
              />
              <Form.Text muted>
                (Пункт 1) Обмеження на максимальну кількість невідомих (макс. {MAX_N_SIZE_CLIENT}).
              </Form.Text>
            </Col>
          </Form.Group>
          
          <hr />
          
          {/* (Пункт "Введення даних") Перемикач Вводу */}
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
                  onChange={() => setInputType('text')}
                />
                <Form.Check
                  inline
                  type="radio"
                  label="Завантажити .txt файл"
                  name="inputType"
                  id="inputTypeFile"
                  checked={inputType === 'file'}
                  onChange={() => setInputType('file')}
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
              />
            </Form.Group>
          ) : (
             <Form.Group controlId="matrixFile" className="mb-3">
              <Form.Label>Файл (.txt)</Form.Label>
              <Form.Control
                type="file"
                accept=".txt, text/plain"
                onChange={handleFileChange}
              />
            </Form.Group>
          )}
          
          <Button type="submit" variant="primary" disabled={loading} className="w-100">
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
      </Card.Body>
    </Card>
  );
};

export default CreateTask;