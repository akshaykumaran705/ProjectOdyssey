"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Bot, Eye, EyeOff, ArrowRight, Stethoscope, ShieldCheck, Activity } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isRegistering) {
        await register(email, password);
      } else {
        await login(email, password);
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel - branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 flex-col justify-between p-12 relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-700/30 rounded-full blur-3xl" />
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-indigo-700/30 rounded-full blur-3xl" />
        </div>

        <div className="relative">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-2.5">
              <Bot className="h-6 w-6 text-white" />
            </div>
            <span className="text-white font-bold text-xl tracking-tight">Project Odyssey</span>
          </div>
          <p className="text-blue-200 text-sm">Clinical Intelligence Platform</p>
        </div>

        <div className="relative space-y-8">
          <div>
            <h1 className="text-4xl font-bold text-white leading-tight">
              AI-Powered Clinical<br />Decision Support
            </h1>
            <p className="text-blue-200 mt-4 text-lg leading-relaxed">
              Transform complex medical records into actionable clinical intelligence in minutes.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-4">
            {[
              { icon: Stethoscope, label: "Differential Diagnosis", desc: "Evidence-grounded AI analysis" },
              { icon: ShieldCheck, label: "Trust & Safety Reports", desc: "Full traceability on every claim" },
              { icon: Activity, label: "Rare Disease Spotlight", desc: "Catch what others miss" },
            ].map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex items-center gap-4 bg-white/10 backdrop-blur-sm rounded-xl px-5 py-4">
                <div className="bg-white/10 rounded-lg p-2 shrink-0">
                  <Icon className="h-5 w-5 text-blue-200" />
                </div>
                <div>
                  <p className="text-white font-semibold text-sm">{label}</p>
                  <p className="text-blue-300 text-xs mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-blue-300 text-xs">
          For clinical decision support only. Not a substitute for professional medical judgment.
        </p>
      </div>

      {/* Right panel - login form */}
      <div className="flex-1 flex items-center justify-center bg-slate-50 p-8">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="bg-blue-600 rounded-lg p-2">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <span className="font-bold text-slate-900">Project Odyssey</span>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900">
              {isRegistering ? "Create your account" : "Welcome back"}
            </h2>
            <p className="text-slate-500 mt-1 text-sm">
              {isRegistering
                ? "Join Project Odyssey to start your first case."
                : "Sign in to access your clinical cases."}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Email address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="doctor@hospital.com"
                className="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-shadow"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="flex h-11 w-full rounded-lg border border-slate-200 bg-white px-4 py-2 pr-10 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-shadow"
                  required
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg gap-2 transition-all"
              disabled={loading}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Please wait...
                </span>
              ) : (
                <>
                  {isRegistering ? "Create Account" : "Sign In"}
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>

            <div className="text-center">
              <button
                type="button"
                className="text-sm text-blue-600 hover:text-blue-700 hover:underline font-medium"
                onClick={() => { setIsRegistering(!isRegistering); setError(""); }}
              >
                {isRegistering ? "Already have an account? Sign in" : "Need an account? Register"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
