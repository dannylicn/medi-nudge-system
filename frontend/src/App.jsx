import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
// PatientsPage merged into DashboardPage
import PatientDetailPage from "./pages/PatientDetailPage";
import EscalationsPage from "./pages/EscalationsPage";
import OcrReviewPage from "./pages/OcrReviewPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import MedicationsPage from "./pages/MedicationsPage";
import DashboardPage from "./pages/DashboardPage";

function RequireAuth({ children }) {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Layout>
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/patients" element={<DashboardPage />} />
                <Route path="/patients/:id" element={<PatientDetailPage />} />
                <Route path="/medications" element={<MedicationsPage />} />
                <Route path="/escalations" element={<EscalationsPage />} />
                <Route path="/ocr-review" element={<OcrReviewPage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
              </Routes>
            </Layout>
          </RequireAuth>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
