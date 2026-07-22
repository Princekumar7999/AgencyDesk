'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const { login, isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [agencyName, setAgencyName] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      if (isSignUp) {
        // Register API call
        const payload = {
          email,
          password,
          full_name: fullName,
          agency_name: agencyName || undefined
        };

        const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        const res = await fetch(`${BACKEND_URL}/api/auth/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Sign up failed.');
        }

        // Auto login on successful registration
        await login(email, password);
      } else {
        // Login
        await login(email, password);
      }
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'An error occurred. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickLogin = async (quickEmail: string) => {
    setError('');
    setSubmitting(true);
    try {
      await login(quickEmail, 'password123');
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Quick login failed.');
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0b0f19]">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-t-transparent border-violet-500"></div>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-[#0b0f19] px-4 py-12">
      {/* Background visual graphics */}
      <div className="absolute top-[-20%] left-[-10%] h-[600px] w-[600px] rounded-full bg-violet-900/10 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-20%] right-[-10%] h-[600px] w-[600px] rounded-full bg-indigo-900/10 blur-[120px] pointer-events-none"></div>

      <div className="w-full max-w-md text-center mb-8">
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-500 bg-clip-text text-transparent">
          AgencyDesk
        </h1>
        <p className="mt-2 text-sm text-gray-400">
          The unified workspace for agency execution and client portals.
        </p>
      </div>

      <div className="w-full max-w-md glass-panel p-8">
        <h2 className="text-2xl font-bold mb-6 text-white text-center">
          {isSignUp ? 'Launch an Agency' : 'Welcome Back'}
        </h2>

        {error && (
          <div className="mb-4 rounded-lg bg-red-950/40 border border-red-500/30 p-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isSignUp && (
            <>
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="Morgan Multi"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="input-field"
                />
              </div>
              
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  Agency Name (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Apex Digital"
                  value={agencyName}
                  onChange={(e) => setAgencyName(e.target.value)}
                  className="input-field"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <input
              type="email"
              required
              placeholder="admin.apex@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Password
            </label>
            <input
              type="password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full btn-primary justify-center mt-6"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-t-transparent border-white"></span>
                Processing...
              </span>
            ) : (
              isSignUp ? 'Create Workspace' : 'Sign In'
            )}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-gray-400">
          <span>
            {isSignUp ? 'Already have an account?' : 'Want to register a new agency?'}
          </span>
          <button
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError('');
            }}
            className="ml-2 font-medium text-violet-400 hover:text-violet-300 transition-colors"
          >
            {isSignUp ? 'Sign In Instead' : 'Sign Up Here'}
          </button>
        </div>
      </div>

      {/* Quick Access Test Sandbox */}
      <div className="w-full max-w-md mt-8 glass-panel p-6 border-violet-500/10">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-violet-400 mb-4 text-center">
          Developer Sandbox Login
        </h3>
        
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleQuickLogin('admin.apex@example.com')}
              className="flex flex-col items-center justify-center p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-violet-500/30 transition-all text-left"
            >
              <span className="text-xs font-bold text-violet-300">Alice (Apex)</span>
              <span className="text-[10px] text-gray-500">Agency Admin</span>
            </button>
            
            <button
              onClick={() => handleQuickLogin('member.apex@example.com')}
              className="flex flex-col items-center justify-center p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-violet-500/30 transition-all text-left"
            >
              <span className="text-xs font-bold text-indigo-300">Bob (Apex)</span>
              <span className="text-[10px] text-gray-500">Agency Member</span>
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleQuickLogin('client.apex@example.com')}
              className="flex flex-col items-center justify-center p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-emerald-500/30 transition-all text-left"
            >
              <span className="text-xs font-bold text-emerald-300">Charlie (Alpha)</span>
              <span className="text-[10px] text-gray-500">Client Portal</span>
            </button>

            <button
              onClick={() => handleQuickLogin('admin.quantum@example.com')}
              className="flex flex-col items-center justify-center p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-purple-500/30 transition-all text-left"
            >
              <span className="text-xs font-bold text-purple-300">Quincy (Quantum)</span>
              <span className="text-[10px] text-gray-500">Quantum Admin</span>
            </button>
          </div>

          <button
            onClick={() => handleQuickLogin('multi.user@example.com')}
            className="w-full flex flex-col items-center justify-center p-2.5 rounded-lg bg-gradient-to-r from-violet-950/40 to-indigo-950/40 hover:from-violet-900/40 hover:to-indigo-900/40 border border-indigo-500/20 hover:border-indigo-400/40 transition-all"
          >
            <span className="text-xs font-extrabold text-indigo-200">Morgan Multi (multi.user@example.com)</span>
            <span className="text-[10px] text-indigo-400 font-semibold mt-0.5">
              Client Portal (Apex) & Agency Member (Quantum)
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
