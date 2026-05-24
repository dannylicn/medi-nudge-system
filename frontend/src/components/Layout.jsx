import { Link, useLocation, useNavigate } from "react-router-dom";
import { useState, useRef, useEffect } from "react";
import { useAuth } from "../hooks/useAuth";
import { getMedications, getPatients } from "../lib/api";

/* ============================================================
   Adheris Layout — Option B
   - 64px warm-cream rail (icon only) collapsed by default
   - Hover or pin → expands to 248px with labels (overlays content)
   - White top utility bar with global search, notifications, user identity
   - Sign out lives in the top-right user dropdown (NOT the rail foot)
   - Global search routes to the most relevant portal page and passes search
     queries through URLs where the page supports filtering.
   ============================================================ */

const NAV = [
  { label: "Dashboard",   to: "/dashboard",   Icon: IconDashboard },
  { label: "Medications", to: "/medications", Icon: IconPill },
  { label: "Escalations", to: "/escalations", Icon: IconBell },
  { label: "Analytics",   to: "/analytics",   Icon: IconChart },
];

const RAIL_COLLAPSED = 64;
const RAIL_EXPANDED  = 248;

export default function Layout({ children }) {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [hover, setHover] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const expanded = hover || pinned;
  const menuRef = useRef(null);

  // Close the user menu when clicking outside
  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [menuOpen]);

  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) {
      navigate("/dashboard");
      return;
    }

    const lower = q.toLowerCase();
    const encoded = encodeURIComponent(q);
    const pageMatches = [
      { terms: ["escalation", "escalations", "alert", "alerts", "urgent"], path: "/escalations" },
      { terms: ["analytics", "analysis", "report", "reports", "trend", "trends", "heatmap"], path: "/analytics" },
      { terms: ["med", "meds", "medication", "medications", "medicine", "medicines", "drug", "drugs", "rx"], path: `/medications?search=${encoded}` },
      { terms: ["patient", "patients", "dashboard"], path: `/dashboard?search=${encoded}` },
    ];
    const matchedPage = pageMatches.find(({ terms }) => terms.some((term) => lower.includes(term)));
    if (matchedPage) {
      navigate(matchedPage.path);
      return;
    }

    try {
      const [{ data: meds }, { data: patientResults }] = await Promise.all([
        getMedications(),
        getPatients({ search: q, page: 1, page_size: 1 }),
      ]);
      const medicationMatch = meds.some((m) =>
        [m.name, m.generic_name, m.category].some((value) => value?.toLowerCase().includes(lower))
      );
      if (medicationMatch) {
        navigate(`/medications?search=${encoded}`);
        return;
      }
      if (patientResults.total > 0) {
        navigate(`/dashboard?search=${encoded}`);
        return;
      }
    } catch {
      // Fall through to patient registry search if classification fails.
    }

    navigate(`/dashboard?search=${encoded}`);
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const initials = (user?.name || user?.email || "U")
    .split(/[\s@.]+/)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() || "")
    .join("") || "U";

  return (
    <div className="flex flex-col min-h-screen bg-surface">
      {/* ============ Top utility bar ============ */}
      <header className="flex items-center gap-4 bg-surface-container-lowest border-b border-outline-variant h-14 pr-6 relative z-20">
        {/* Brand block aligns with rail width */}
        <div
          style={{ width: RAIL_COLLAPSED }}
          className="h-14 flex items-center justify-center bg-surface-container-low border-r border-outline-variant flex-shrink-0"
        >
          <span className="adheris-brand-dot" />
        </div>

        <div className="flex-1" />

        {/* Global search — submits to /dashboard?search=… */}
        <form onSubmit={handleSearchSubmit} className="relative w-[360px] max-w-[40%]">
          <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search patients, medications…"
            aria-label="Global search"
            className="w-full rounded-pill border border-outline-variant bg-surface pl-10 pr-4 py-2 font-body text-sm text-on-surface placeholder-muted outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15 transition"
          />
        </form>

        {/* User identity + dropdown menu (sign out lives here) */}
        <div ref={menuRef} className="relative">
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            className={`flex items-center gap-2.5 pl-1 pr-2.5 py-1 rounded-pill border border-transparent transition-colors ${
              menuOpen ? "bg-surface-container-low" : "hover:bg-surface-container-low"
            }`}
          >
            <div className="w-8 h-8 rounded-full flex items-center justify-center font-display text-[13px] font-medium text-white bg-gradient-to-br from-gold to-accent">
              {initials}
            </div>
            <div className="leading-tight text-[13px] text-left">
              <div className="font-semibold text-on-surface">{user?.name || user?.email || "User"}</div>
              <div className="text-[11px] text-muted">Care coordinator</div>
            </div>
            <svg
              className={`text-muted transition-transform ${menuOpen ? "rotate-180" : ""}`}
              width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>

          {menuOpen && (
            <div
              role="menu"
              className="absolute right-0 top-full mt-2 min-w-[240px] bg-surface-container-lowest border border-outline-variant rounded-2xl shadow-float p-1.5 z-50"
            >
              <div className="px-3 pt-2.5 pb-3 border-b border-outline-variant mb-1.5">
                <div className="text-[13px] font-semibold text-on-surface">{user?.name || user?.email || "User"}</div>
                {user?.email && (
                  <div className="text-[11px] text-muted mt-0.5 truncate">{user.email}</div>
                )}
              </div>
              <MenuItem
                icon={<IconSignOut />}
                label="Sign out"
                accent
                onClick={() => { setMenuOpen(false); handleLogout(); }}
              />
            </div>
          )}
        </div>
      </header>

      {/* ============ Body ============ */}
      <div className="flex flex-1 relative">
        {/* Spacer — reserves the collapsed rail width so content doesn't shift on hover */}
        <div style={{ width: RAIL_COLLAPSED }} className="flex-shrink-0" />

        {/* Floating rail */}
        <aside
          onMouseEnter={() => setHover(true)}
          onMouseLeave={() => setHover(false)}
          style={{
            width: expanded ? RAIL_EXPANDED : RAIL_COLLAPSED,
            transition: "width .22s cubic-bezier(.2,.7,.2,1), box-shadow .22s ease",
            boxShadow: expanded && !pinned
              ? "0 24px 60px rgba(14,26,43,.10)"
              : "none",
          }}
          className="absolute inset-y-0 left-0 bg-surface-container-low border-r border-outline-variant flex flex-col overflow-hidden z-10"
        >
          {/* Brand row inside rail */}
          <div
            className={`h-14 flex items-center border-b border-outline-variant flex-shrink-0 ${
              expanded ? "px-4 justify-between" : "justify-center"
            }`}
          >
            {expanded && (
              <div>
                <div className="font-display text-[19px] font-medium tracking-tightish text-on-surface whitespace-nowrap leading-none">
                  Adheris
                </div>
                <div className="font-body text-[10px] uppercase tracking-eyebrow font-medium text-muted mt-1 whitespace-nowrap">
                  Care Coordinator
                </div>
              </div>
            )}
            {expanded && (
              <button
                type="button"
                onClick={() => setPinned((p) => !p)}
                title={pinned ? "Unpin sidebar" : "Pin sidebar open"}
                aria-pressed={pinned}
                className={`w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
                  pinned
                    ? "bg-accent text-white"
                    : "border border-outline-variant text-on-surface/60 hover:bg-surface-container-highest"
                }`}
              >
                <PinIcon filled={pinned} />
              </button>
            )}
          </div>

          {/* Nav */}
          <nav className="flex-1 px-2.5 py-3 flex flex-col gap-0.5">
            {NAV.map(({ label, to, Icon }) => {
              const isActive = pathname.startsWith(to);
              return (
                <Link
                  key={to}
                  to={to}
                  title={!expanded ? label : undefined}
                  className={`flex items-center h-11 rounded-xl text-[13.5px] font-semibold transition-colors ${
                    expanded ? "px-3 gap-3.5 justify-start" : "justify-center"
                  } ${
                    isActive
                      ? "bg-ink text-surface"
                      : "text-on-surface/70 hover:bg-ink/5"
                  }`}
                >
                  <span
                    className={`w-6 flex justify-center flex-shrink-0 ${
                      isActive ? "text-accent" : "text-muted"
                    }`}
                  >
                    <Icon />
                  </span>
                  {expanded && <span className="whitespace-nowrap">{label}</span>}
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Main */}
        <main className="flex-1 bg-surface min-w-0 relative">{children}</main>
      </div>
    </div>
  );
}

/* ============================================================
   Inline SVG icons — thin, calm, healthcare-feeling
   ============================================================ */
function SvgBase({ children, size = 18 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

function IconDashboard() {
  return (
    <SvgBase>
      <rect x="3" y="3" width="8" height="8" rx="2" />
      <rect x="13" y="3" width="8" height="5" rx="2" />
      <rect x="13" y="10" width="8" height="11" rx="2" />
      <rect x="3" y="13" width="8" height="8" rx="2" />
    </SvgBase>
  );
}
function IconPill() {
  return (
    <SvgBase>
      <path d="M10 2.5 2.5 10a4.95 4.95 0 0 0 7 7L17 9.5a4.95 4.95 0 0 0-7-7Z" />
      <path d="m8.5 8.5 7 7" />
    </SvgBase>
  );
}
function IconBell() {
  return (
    <SvgBase>
      <path d="M6 8a6 6 0 1 1 12 0c0 4 2 5 2 7H4c0-2 2-3 2-7Z" />
      <path d="M10 21a2 2 0 0 0 4 0" />
    </SvgBase>
  );
}
function IconChart() {
  return (
    <SvgBase>
      <path d="M3 3v18h18" />
      <path d="M7 14l4-4 3 3 5-6" />
    </SvgBase>
  );
}
function IconSignOut() {
  return (
    <SvgBase>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </SvgBase>
  );
}
function SearchIcon({ className = "" }) {
  return (
    <svg
      className={className}
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  );
}
function PinIcon({ filled = false }) {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 2 L8 6 L8 11 L4 14 L4 16 L11 16 L11 22 L13 22 L13 16 L20 16 L20 14 L16 11 L16 6 Z" />
    </svg>
  );
}

/* ============================================================
   User menu — dropdown item + extra icons
   ============================================================ */
function MenuItem({ icon, label, accent = false, onClick }) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className={`flex items-center gap-2.5 w-full px-2.5 py-2 rounded-lg font-body text-[13px] text-left transition-colors ${
        accent
          ? "text-accent font-semibold hover:bg-error-container"
          : "text-on-surface font-medium hover:bg-surface-container-low"
      }`}
    >
      <span className={`w-4 flex items-center justify-center ${accent ? "text-accent" : "text-muted"}`}>
        {icon}
      </span>
      {label}
    </button>
  );
}

function IconUser() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  );
}
function IconSettings() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>
    </svg>
  );
}
function IconHelp() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}
