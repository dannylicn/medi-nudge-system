import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/patients");
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[1.05fr_1fr] bg-surface">
      {/* ============ Left panel — brand narrative ============ */}
      <div className="relative hidden lg:flex flex-col justify-between bg-surface-container-low px-16 py-16 overflow-hidden">
        {/* Soft radial wash */}
        <div
          aria-hidden="true"
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 20%, rgba(232,90,60,.10), transparent 55%), radial-gradient(circle at 80% 80%, rgba(15,76,92,.08), transparent 55%)",
          }}
        />

        <div className="relative">
          <div className="adheris-brand text-[26px]">
            <span className="adheris-brand-dot" />
            Adheris
          </div>
        </div>

        <div className="relative">
          <div className="eyebrow mb-3">For care teams</div>
          <h1 className="font-display text-[56px] font-normal leading-[1.02] tracking-[-0.03em] max-w-[12ch] text-on-surface">
            Medication adherence that <em>actually works.</em>
          </h1>
          <p className="mt-6 font-body text-base text-ink-soft max-w-[40ch] leading-relaxed">
            A medication adherence system for chronic-disease patients in
            Singapore — built for the nurses and doctors who keep them on
            track.
          </p>
        </div>

        {/* spacer keeps the brand anchored to the top and the copy centered */}
        <div className="relative" />
      </div>

      {/* ============ Right panel — sign-in card ============ */}
      <div className="flex items-center justify-center px-6 py-16 lg:px-16">
        <div className="w-full max-w-sm bg-surface-container-lowest border border-outline-variant rounded-2xl shadow-ambient p-8">
          <div className="eyebrow">Sign in</div>
          <h2 className="font-display text-3xl font-normal text-on-surface mt-2 mb-1 tracking-tightish">
            Welcome back.
          </h2>
          <p className="font-body text-sm text-ink-soft mb-7">
            Care Coordinator Portal · v2.4
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="email"
                className="block font-body text-[11px] font-semibold tracking-eyebrow uppercase text-muted mb-1.5"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="w-full rounded-xl border border-outline-variant bg-surface px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15 transition"
              />
            </div>
            <div>
              <label
                htmlFor="password"
                className="block font-body text-[11px] font-semibold tracking-eyebrow uppercase text-muted mb-1.5"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="w-full rounded-xl border border-outline-variant bg-surface px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/15 transition"
              />
            </div>

            {error && (
              <p className="font-body text-sm text-accent bg-error-container px-3.5 py-2.5 rounded-xl">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-ink text-surface rounded-pill py-3 font-body text-sm font-semibold disabled:opacity-60 transition-colors hover:bg-accent"
            >
              {loading ? "Signing in…" : "Sign in →"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
