// frontend/src/contexts/AuthContext.jsx
import React, { createContext, useState, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode'; // Зверніть увагу на імпорт
import api from '../api/axiosConfig';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [authTokens, setAuthTokens] = useState(() => 
    localStorage.getItem('authTokens')
      ? JSON.parse(localStorage.getItem('authTokens'))
      : null
  );
  
  const [user, setUser] = useState(() => 
    localStorage.getItem('authTokens')
      ? jwtDecode(JSON.parse(localStorage.getItem('authTokens')).access)
      : null
  );

  const [loading, setLoading] = useState(true);

  const loginUser = async (username, password) => {
    try {
      const response = await api.post('/users/login/', { username, password });
      const data = response.data;
      setAuthTokens(data);
      setUser(jwtDecode(data.access));
      localStorage.setItem('authTokens', JSON.stringify(data));
      return { success: true };
    } catch (error) {
      console.error("Login error", error);
      const errorMsg = error.response?.data?.detail || "Помилка входу";
      return { success: false, error: errorMsg };
    }
  };

  const logoutUser = () => {
    setAuthTokens(null);
    setUser(null);
    localStorage.removeItem('authTokens');
  };

  const registerUser = async (username, email, password, password2) => {
     try {
      await api.post('/users/register/', {
        username,
        email,
        password,
        password2,
      });
      // Автоматично логінимо користувача після реєстрації
      return await loginUser(username, password);
    } catch (error) {
      console.error("Register error", error);
      const errorMsg = error.response?.data?.email?.[0] || error.response?.data?.username?.[0] || "Помилка реєстрації";
      return { success: false, error: errorMsg };
    }
  };

  // Ефект для оновлення токену (виконується при завантаженні)
  useEffect(() => {
    // Ми не будемо тут оновлювати токен, 
    // це зробить `axiosConfig` при першому запиті.
    // Тут ми просто прибираємо завантаження.
    setLoading(false); 
  }, [authTokens]);

  const contextData = {
    user,
    authTokens,
    loginUser,
    logoutUser,
    registerUser,
  };

  return (
    <AuthContext.Provider value={contextData}>
      {loading ? null : children}
    </AuthContext.Provider>
  );
};

export default AuthContext;