"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { User, Organization, AuthResponse } from "./types";
import { api, setStoredSession, clearStoredSession } from "./api";

interface AuthContextType {
  user: User | null;
  organization: Organization | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<AuthResponse>;
  signup: (payload: {
    full_name: string;
    email: string;
    password: string;
    company_name?: string;
  }) => Promise<AuthResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  const refreshUser = async () => {
    try {
      const data = await api.getMe();
      if (data && data.user) {
        setUser(data.user);
        setOrganization(data.organization);
        if (data.access_token) {
          setStoredSession(data.access_token);
        }
      } else {
        setUser(null);
        setOrganization(null);
      }
    } catch (err) {
      setUser(null);
      setOrganization(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email: string, password: string): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      const res: AuthResponse = await api.login({ email, password });
      setUser(res.user);
      setOrganization(res.organization);
      setStoredSession(res.access_token);
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (payload: {
    full_name: string;
    email: string;
    password: string;
    company_name?: string;
  }): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      const res: AuthResponse = await api.signup(payload);
      setUser(res.user);
      setOrganization(res.organization);
      setStoredSession(res.access_token);
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await api.logout();
    } catch (err) {
      console.warn("Logout warning:", err);
    } finally {
      clearStoredSession();
      setUser(null);
      setOrganization(null);
      setIsLoading(false);
      window.location.href = "/login";
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        organization,
        isLoading,
        isAuthenticated: !!user,
        login,
        signup,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
