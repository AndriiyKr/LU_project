import axios from 'axios';
import { jwtDecode } from 'jwt-decode';

const baseURL = '/api'; 
const api = axios.create({
  baseURL,
});

api.interceptors.request.use(
  async (config) => {
    let authTokens = localStorage.getItem('authTokens')
      ? JSON.parse(localStorage.getItem('authTokens'))
      : null;

    if (authTokens) {
      const accessToken = authTokens.access;
      const user = jwtDecode(accessToken);
      const isExpired = Date.now() >= user.exp * 1000;

      if (!isExpired) {
        config.headers.Authorization = `Bearer ${accessToken}`;
        return config;
      }

      try {
        const response = await axios.post(`${baseURL}/users/login/refresh/`, {
          refresh: authTokens.refresh,
        });

        const newTokens = { ...authTokens, ...response.data };
        localStorage.setItem('authTokens', JSON.stringify(newTokens));

        config.headers.Authorization = `Bearer ${newTokens.access}`;
        return config;
        
      } catch (refreshError) {
        console.error('Refresh token expired, logging out.', refreshError);
        localStorage.removeItem('authTokens');
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