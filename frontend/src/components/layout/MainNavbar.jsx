// frontend/src/components/layout/MainNavbar.jsx
import React from 'react';
import { Navbar, Nav, Container, Button } from 'react-bootstrap';
import { LinkContainer } from 'react-router-bootstrap';
import useAuth from '../../hooks/useAuth';

const MainNavbar = () => {
  const { user, logoutUser } = useAuth();

  return (
    <Navbar bg="dark" variant="dark" expand="lg" collapseOnSelect>
      <Container>
        <LinkContainer to="/">
          <Navbar.Brand>LU Solver</Navbar.Brand>
        </LinkContainer>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            {user && (
              <>
                <LinkContainer to="/">
                  <Nav.Link>Панель Задач</Nav.Link>
                </LinkContainer>
                <LinkContainer to="/create-task">
                  <Nav.Link>Створити Задачу</Nav.Link>
                </LinkContainer>
                {/* (Пункт 8) */}
                {user.is_staff && ( 
                  <LinkContainer to="/admin">
                    <Nav.Link className="text-warning">Адмін-Панель</Nav.Link>
                  </LinkContainer>
                )}
              </>
            )}
          </Nav>
          <Nav>
            {user ? (
              <>
                <Navbar.Text className="me-3">
                  Вітаємо, {user.username}
                </Navbar.Text>
                <Button variant="outline-light" onClick={logoutUser}>
                  Вийти
                </Button>
              </>
            ) : (
              <>
                <LinkContainer to="/login">
                  <Nav.Link>Увійти</Nav.Link>
                </LinkContainer>
                <LinkContainer to="/register">
                  <Nav.Link>Реєстрація</Nav.Link>
                </LinkContainer>
              </>
            )}
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default MainNavbar;