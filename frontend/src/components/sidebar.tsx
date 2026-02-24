"use client";

import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Bot, LogOut, Activity, LayoutDashboard, ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
    { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { href: "/metrics", icon: Activity, label: "System Metrics" },
];

export function Sidebar() {
    const { logout, isAuthenticated } = useAuth();
    const pathname = usePathname();

    if (!isAuthenticated) return null;

    return (
        <div className="flex h-screen w-60 flex-col bg-slate-900 text-white">
            {/* Logo */}
            <div className="flex h-16 items-center gap-3 px-5 border-b border-slate-800">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
                    <Bot className="h-4 w-4 text-white" />
                </div>
                <div>
                    <p className="text-sm font-bold leading-none">Project Odyssey</p>
                    <p className="text-[10px] text-slate-400 mt-0.5 leading-none">Clinical AI Platform</p>
                </div>
            </div>

            {/* Nav */}
            <div className="flex-1 overflow-auto py-6 px-3 space-y-1">
                <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest px-3 mb-3">Navigation</p>
                {navItems.map(({ href, icon: Icon, label }) => {
                    const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
                    return (
                        <Link
                            key={href}
                            href={href}
                            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all group ${active
                                    ? "bg-blue-600 text-white shadow-lg shadow-blue-900/30"
                                    : "text-slate-400 hover:bg-slate-800 hover:text-white"
                                }`}
                        >
                            <Icon className="h-4 w-4 shrink-0" />
                            <span className="flex-1">{label}</span>
                            {active && <ChevronRight className="h-3.5 w-3.5 opacity-60" />}
                        </Link>
                    );
                })}
            </div>

            {/* Bottom */}
            <div className="border-t border-slate-800 p-3">
                <button
                    onClick={logout}
                    className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-all"
                >
                    <LogOut className="h-4 w-4" />
                    Log out
                </button>
            </div>
        </div>
    );
}
