import React from 'react';
import { Alert, Container } from 'react-bootstrap';
import { Link } from 'react-router-dom';

const NotFound = () => {
  return (
    <Container className="text-center mt-5">
      <Alert variant="danger">
        <Alert.Heading>Помилка 404</Alert.Heading>
        <p>
          Сторінку, яку ви шукаєте, не знайдено.
        </p>
        <hr />
        <Link to="/" className="btn btn-primary">
          На Головну
        </Link>
      </Alert>
    </Container>
  );
};

export default NotFound;