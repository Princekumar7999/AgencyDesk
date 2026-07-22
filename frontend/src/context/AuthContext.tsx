'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export interface AgencyMembershipInfo {
  agency_id: string;
  agency_name: string;
  role: string; // agency_admin, agency_member, client_user
  client_id: string | null;
  client_name: string | null;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  memberships: AgencyMembershipInfo[];
}

interface AuthContextType {
  user: UserProfile | null;
  activeMembership: AgencyMembershipInfo | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  switchAgency: (agencyId: string) => void;
  refreshProfile: () => Promise<void>;
  apiFetch: (path: string, options?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeMembership, setActiveMembership] = useState<AgencyMembershipInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Load user and select active workspace on mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return;
    }
    
    fetchProfile(token);
  }, []);

  const fetchProfile = async (token: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!res.ok) {
        throw new Error('Failed to fetch user profile');
      }

      const data: UserProfile = await res.json();
      setUser(data);

      if (data.memberships && data.memberships.length > 0) {
        // Retrieve last active agency from storage, or default to first membership
        const savedAgencyId = localStorage.getItem('active_agency_id');
        const match = data.memberships.find(m => m.agency_id === savedAgencyId);
        const selected = match || data.memberships[0];
        
        setActiveMembership(selected);
        localStorage.setItem('active_agency_id', selected.agency_id);
      } else {
        setActiveMembership(null);
      }
    } catch (err) {
      console.error(err);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString()
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Login failed. Invalid email or password.');
      }

      const { access_token } = await res.json();
      localStorage.setItem('token', access_token);
      await fetchProfile(access_token);
    } catch (err) {
      setLoading(false);
      throw err;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('active_agency_id');
    setUser(null);
    setActiveMembership(null);
    setLoading(false);
    router.push('/');
  };

  const switchAgency = (agencyId: string) => {
    if (!user) return;
    const match = user.memberships.find(m => m.agency_id === agencyId);
    if (match) {
      setActiveMembership(match);
      localStorage.setItem('active_agency_id', match.agency_id);
      // Trigger a soft refresh by reloading dashboard state
      router.refresh();
    }
  };

  const refreshProfile = async () => {
    const token = localStorage.getItem('token');
    if (token) {
      await fetchProfile(token);
    }
  };

  // Central fetch wrapper that intercepts and injects auth token + tenant scope headers
  const apiFetch = async (path: string, options: RequestInit = {}): Promise<Response> => {
    const token = localStorage.getItem('token');
    const headers = new Headers(options.headers || {});

    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    if (activeMembership) {
      headers.set('X-Agency-ID', activeMembership.agency_id);
    }

    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return fetch(`${BACKEND_URL}/api${cleanPath}`, {
      ...options,
      headers
    });
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        activeMembership,
        isAuthenticated: !!user,
        loading,
        login,
        logout,
        switchAgency,
        refreshProfile,
        apiFetch
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
