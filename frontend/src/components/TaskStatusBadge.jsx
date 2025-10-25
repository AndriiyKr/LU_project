// frontend/src/components/TaskStatusBadge.jsx
import React from 'react';
import { Badge } from 'react-bootstrap';

const TaskStatusBadge = ({ status }) => {
  const variants = {
    pending: 'secondary',
    queued: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    cancelled: 'warning',
  };

  const text = {
    pending: 'В очікуванні',
    queued: 'В черзі',
    running: 'Виконується',
    completed: 'Завершено',
    failed: 'Помилка',
    cancelled: 'Скасовано',
  };

  return (
    <Badge bg={variants[status] || 'light'}>
      {text[status] || status}
    </Badge>
  );
};

export default TaskStatusBadge;