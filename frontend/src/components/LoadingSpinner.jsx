import React from 'react';
import { Spinner } from 'react-bootstrap';

const LoadingSpinner = ({ text = "Завантаження..." }) => {
  return (
    <div className="d-flex justify-content-center align-items-center my-5">
      <Spinner animation="border" role="status" className="me-3">
        <span className="visually-hidden">{text}</span>
      </Spinner>
      <span>{text}</span>
    </div>
  );
};

export default LoadingSpinner;