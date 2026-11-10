import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, endpoints } from '../api/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('token');
    if (token) {
      checkAuthStatus();
    } else {
      setLoading(false);
    }
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await api.get(endpoints.auth.me);
      setUser(response.data);
    } catch (error) {
      console.error('Auth check failed:', error);
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    // Clear any previous error before attempting login
    setError(null);
    
    try {
      const response = await api.post(endpoints.auth.login, { email, password });
      const { access_token, ...userData } = response.data;
      
      localStorage.setItem('token', access_token);
      setUser(userData);
      setError(null);
      
      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Invalid email or password';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const signup = async (userData) => {
    try {
      const response = await api.post(endpoints.auth.signup, userData);
      const { access_token, ...createdUserData } = response.data;
      
      localStorage.setItem('token', access_token);
      setUser(createdUserData);
      setError(null); // Only clear error on successful signup
      
      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Signup failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('loginError'); // Clear any stored errors
    setUser(null);
    setError(null);
    // Note: Favorites are now stored in the database and persist across sessions
  };

  const clearError = () => {
    setError(null);
  };

  const clearErrorWithDelay = () => {
    setTimeout(() => {
      setError(null);
    }, 5000); // Clear error after 5 seconds
  };

  const clearAllUserData = () => {
    localStorage.removeItem('token');
    setUser(null);
    setError(null);
    // Note: Favorites are stored in the database and persist across sessions
  };

  const value = {
    user,
    loading,
    error,
    login,
    signup,
    logout,
    clearError,
    clearErrorWithDelay,
    clearAllUserData,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
