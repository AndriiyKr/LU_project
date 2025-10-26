// frontend/src/components/routes/AdminRoute.jsx
import { Navigate, Outlet } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';
import NotFound from '../../pages/NotFound';

const AdminRoute = () => {
  const { user } = useAuth();
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // user.is_staff приходить з JWT токену (треба додати в backend)
  // Поки що перевіряємо username
  // TODO: Обов'язково додати 'is_staff' в JWT payload на backend!
  
  // Припускаємо, що токен містить is_staff (якщо ні, додайте в backend)
  // const decoded = jwtDecode(authTokens.access); 
  // if (decoded.is_staff) ...
  
  return user.is_staff ? <Outlet /> : <NotFound />;
};

export default AdminRoute;