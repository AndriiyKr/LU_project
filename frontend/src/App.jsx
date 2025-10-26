// frontend/src/App.jsx
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Container } from 'react-bootstrap';
import MainNavbar from './components/layout/MainNavbar';
import PrivateRoute from './components/routes/PrivateRoute';
import AdminRoute from './components/routes/AdminRoute';

// Сторінки
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import CreateTask from './pages/CreateTask';
import TaskDetail from './pages/TaskDetail';
import AdminDashboard from './pages/AdminDashboard'; // (Пункт 8)
import NotFound from './pages/NotFound';

function App() {
  return (
    <>
      <MainNavbar />
      <Container className="mt-4">
        <Routes>
          {/* Публічні маршрути */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Приватні маршрути (для всіх залогінених) */}
          <Route element={<PrivateRoute />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/create-task" element={<CreateTask />} />
            <Route path="/task/:id" element={<TaskDetail />} />
          </Route>
          
          {/* Маршрути для Адміністратора (Пункт 8) */}
          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminDashboard />} />
          </Route>

          {/* 404 */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Container>
    </>
  );
}

export default App;