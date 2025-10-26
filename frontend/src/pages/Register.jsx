// frontend/src/pages/Register.jsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { Form, Button, Card, Alert, Container } from 'react-bootstrap';

const Register = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [error, setError] = useState('');
  const { registerUser } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== password2) {
      setError('Паролі не збігаються');
      return;
    }
    
    const result = await registerUser(username, email, password, password2);
    
    if (result.success) {
      navigate('/'); // Успішна реєстрація та логін
    } else {
      setError(result.error);
    }
  };

  return (
    <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '80vh' }}>
      <Card style={{ width: '400px' }}>
        <Card.Body>
          <h2 className="text-center mb-4">Реєстрація</h2>
          {error && <Alert variant="danger">{error}</Alert>}
          <Form onSubmit={handleSubmit}>
            <Form.Group id="username" className="mb-3">
              <Form.Label>Ім'я користувача</Form.Label>
              <Form.Control type="text" onChange={(e) => setUsername(e.target.value)} required />
            </Form.Group>
            <Form.Group id="email" className="mb-3">
              <Form.Label>Email</Form.Label>
              <Form.Control type="email" onChange={(e) => setEmail(e.target.value)} required />
            </Form.Group>
            <Form.Group id="password"  className="mb-3">
              <Form.Label>Пароль</Form.Label>
              <Form.Control type="password" onChange={(e) => setPassword(e.target.value)} required />
            </Form.Group>
            <Form.Group id="password2"  className="mb-3">
              <Form.Label>Підтвердіть пароль</Form.Label>
              <Form.Control type="password" onChange={(e) => setPassword2(e.target.value)} required />
            </Form.Group>
            <Button type="submit" className="w-100">
              Зареєструватись
            </Button>
          </Form>
        </Card.Body>
        <Card.Footer className="text-muted text-center">
          Вже маєте акаунт? <Link to="/login">Увійти</Link>
        </Card.Footer>
      </Card>
    </Container>
  );
};

export default Register;