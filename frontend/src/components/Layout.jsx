import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const NAV = [
  { label: "Patients", to: "/patients", icon: "👥" },
  { label: "Escalations", to: "/escalations", icon: "🚨" },
  { label: "OCR Review", to: "/ocr-review", icon: "📷" },
  { label: "Analytics", to: "/analytics", icon: "📊" },
];

export default function Layout({ children }) {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-surface">
      {/* Sidebar — no border, background shift only */}
      <aside className="w-56 bg-surface-container-low flex flex-col shadow-ambient">
        <div className="px-5 py-5">
          <span className="font-display text-lg font-bold text-primary tracking-tight">
            MediNudge
          </span>
          <p className="font-body text-xs text-on-surface/50 mt-0.5">Care Coordinator</p>
        </div>
        <nav className="flex-1 py-3 space-y-0.5 px-3">
          {NAV.map(({ label, to, icon }) => (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                pathname.startsWith(to)
                  ? "bg-primary/10 text-primary"
                  : "text-on-surface/60 hover:bg-surface-container-highest/60"
              }`}
            >
              <span>{icon}</span>
              {label}
            </Link>
          ))}
        </nav>
        <div className="px-4 py-4 bg-surface-container-lowest/60">
          <p className="font-body text-xs text-on-surface/50 mb-2">{user?.email}</p>
          <button
            onClick={handleLogout}
            className="font-body text-xs text-error hover:text-error/80 text-left"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto bg-surface">{children}</main>
    </div>
  );
}
