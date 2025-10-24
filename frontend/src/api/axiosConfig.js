// frontend/src/api/axiosConfig.js
import axios from 'axios';
import { jwtDecode } from 'jwt-decode';

// Базовий URL для всіх API-запитів
const baseURL = '/api'; // Nginx буде проксіювати це

const api = axios.create({
  baseURL,
});

// Interceptor (перехоплювач) для додавання Auth токену до запитів
api.interceptors.request.use(
  async (config) => {
    let authTokens = localStorage.getItem('authTokens')
      ? JSON.parse(localStorage.getItem('authTokens'))
      : null;

    if (authTokens) {
      // Перевіряємо, чи токен не прострочився
      const accessToken = authTokens.access;
      const user = jwtDecode(accessToken);
      const isExpired = Date.now() >= user.exp * 1000;

      if (!isExpired) {
        config.headers.Authorization = `Bearer ${accessToken}`;
        return config;
      }

      // Токен прострочився, оновлюємо його
      try {
        const response = await axios.post(`${baseURL}/users/login/refresh/`, {
          refresh: authTokens.refresh,
        });

        // Оновлюємо токени в localStorage
        const newTokens = { ...authTokens, ...response.data };
        localStorage.setItem('authTokens', JSON.stringify(newTokens));

        // Оновлюємо заголовок в поточному запиті
        config.headers.Authorization = `Bearer ${newTokens.access}`;
        return config;
        
      } catch (refreshError) {
        // Помилка оновлення (напр. refresh токен теж прострочився)
        console.error('Refresh token expired, logging out.', refreshError);
        localStorage.removeItem('authTokens');
        // Перезавантажуємо сторінку, щоб перекинути на логін
        window.location.href = '/login'; 
        return Promise.reject(refreshError);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;