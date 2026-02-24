"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { login as apiLogin, register as apiRegister } from "@/lib/api";

interface AuthContextType {
    token: string | null;
    login: (email: string, pass: string) => Promise<void>;
    register: (email: string, pass: string) => Promise<void>;
    logout: () => void;
    isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [token, setToken] = useState<string | null>(null);
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        const t = localStorage.getItem("odyssey_token");
        if (t) setToken(t);
        else if (pathname !== "/") {
            router.push("/");
        }
    }, [pathname, router]);

    const login = async (email: string, pass: string) => {
        const res = await apiLogin(email, pass);
        setToken(res.access_token);
        router.push("/dashboard");
    };

    const register = async (email: string, pass: string) => {
        await apiRegister(email, pass);
        await login(email, pass);
    };

    const logout = () => {
        localStorage.removeItem("odyssey_token");
        setToken(null);
        router.push("/");
    };

    return (
        <AuthContext.Provider value={{ token, login, register, logout, isAuthenticated: !!token }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
};
