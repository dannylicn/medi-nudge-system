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
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      {/* Glassmorphism card */}
      <div className="bg-surface-container-lowest/80 backdrop-blur-[20px] rounded-2xl shadow-float w-full max-w-sm p-8">
        <h1 className="font-display text-3xl font-bold text-primary tracking-tight mb-1">
          MediNudge
        </h1>
        <p className="font-body text-sm text-on-surface/50 mb-8">Care Coordinator Portal</p>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed transition-shadow"
              required
              autoComplete="email"
            />
          </div>
          <div>
            <label className="block font-body text-xs font-medium text-on-surface/70 mb-1.5">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-surface-container-highest rounded-xl px-3.5 py-2.5 font-body text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary-fixed transition-shadow"
              required
              autoComplete="current-password"
            />
          </div>

          {error && (
            <p className="font-body text-sm text-error bg-error-container px-3.5 py-2.5 rounded-xl">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-br from-primary to-primary-container text-white rounded-pill py-2.5 font-body text-sm font-semibold disabled:opacity-60 transition-opacity"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
