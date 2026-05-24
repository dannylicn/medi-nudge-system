import { createContext, useContext, useState, useCallback } from "react";
import { login as apiLogin, setToken, clearToken } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // Restore session on refresh — if token exists, user stays logged in
  const [user, setUser] = useState(() => {
    const email = sessionStorage.getItem("user_email");
    return email ? { email } : null;
  });

  const login = useCallback(async (email, password) => {
    const { data } = await apiLogin(email, password);
    setToken(data.access_token);
    sessionStorage.setItem("user_email", email);
    setUser({ email });
    return data;
  }, []);

  const logout = useCallback(() => {
    clearToken();
    sessionStorage.removeItem("user_email");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext);
