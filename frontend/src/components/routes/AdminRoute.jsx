// frontend/src/components/routes/AdminRoute.jsx
import { Navigate, Outlet } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';
import NotFound from '../../pages/NotFound';

const AdminRoute = () => {
  const { user } = useAuth();
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return user.is_staff ? <Outlet /> : <NotFound />;
};

export default AdminRoute;