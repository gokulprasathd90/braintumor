import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import SessionExpiredDialog from './components/SessionExpiredDialog';

// Legacy pages (keep existing routes working)
import Home       from './pages/Home';
import Detect     from './pages/Detect';
import Results    from './pages/Results';

// New pages
import Dashboard           from './pages/Dashboard';
import SinglePrediction    from './pages/SinglePrediction';
import BatchPrediction     from './pages/BatchPrediction';
import Training            from './pages/Training';
import Experiments         from './pages/Experiments';
import DatasetManager      from './pages/DatasetManager';
import ModelManager        from './pages/ModelManager';
import PreprocessingPreview from './pages/PreprocessingPreview';
import Monitoring from './pages/Monitoring';
import Login from './pages/Login';

// Wrapper to conditionally render the Navbar (hidden on /login page)
function MainLayout() {
  const location = useLocation();
  const isLoginPage = location.pathname === '/login';

  return (
    <>
      {!isLoginPage && <Navbar />}
      <Routes>
        {/* Public Login Page */}
        <Route path="/login" element={<Login />} />

        {/* Protected Dashboard/Viewer Routes */}
        <Route path="/"              element={<ProtectedRoute minRole="viewer"><Dashboard /></ProtectedRoute>} />
        <Route path="/experiments"   element={<ProtectedRoute minRole="viewer"><Experiments /></ProtectedRoute>} />
        <Route path="/monitoring"    element={<ProtectedRoute minRole="viewer"><Monitoring /></ProtectedRoute>} />

        {/* Protected Operator Routes */}
        <Route path="/predict"       element={<ProtectedRoute minRole="operator"><SinglePrediction /></ProtectedRoute>} />
        <Route path="/batch"         element={<ProtectedRoute minRole="operator"><BatchPrediction /></ProtectedRoute>} />
        <Route path="/models"        element={<ProtectedRoute minRole="operator"><ModelManager /></ProtectedRoute>} />
        <Route path="/preprocessing" element={<ProtectedRoute minRole="operator"><PreprocessingPreview /></ProtectedRoute>} />

        {/* Protected Researcher Routes */}
        <Route path="/training"      element={<ProtectedRoute minRole="researcher"><Training /></ProtectedRoute>} />
        <Route path="/dataset"       element={<ProtectedRoute minRole="researcher"><DatasetManager /></ProtectedRoute>} />

        {/* Legacy routes — protected for all authenticated users */}
        <Route path="/home"    element={<ProtectedRoute minRole="viewer"><Home /></ProtectedRoute>} />
        <Route path="/detect"  element={<ProtectedRoute minRole="viewer"><Detect /></ProtectedRoute>} />
        <Route path="/results" element={<ProtectedRoute minRole="viewer"><Results /></ProtectedRoute>} />

        {/* Catch-all — redirects to home/dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <SessionExpiredDialog />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <MainLayout />
      </BrowserRouter>
    </AuthProvider>
  );
}
