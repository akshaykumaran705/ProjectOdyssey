/* ── API Client for ProjectOdyssey ─────────────────────────── */

const BASE = "/api";

function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("odyssey_token");
}

async function request<T>(
    path: string,
    opts: RequestInit = {}
): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = {
        ...(opts.headers as Record<string, string>),
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (!(opts.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    const res = await fetch(`${BASE}${path}`, { ...opts, headers });
    if (!res.ok) {
        const text = await res.text().catch(() => "Unknown error");
        throw new Error(`${res.status}: ${text}`);
    }
    return res.json();
}

/* ── Auth ──────────────────────────────────────────────────── */
export async function login(email: string, password: string) {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const data = await fetch(`${BASE}/auth/login`, {
        method: "POST",
        body: form,
    }).then(async (r) => {
        if (!r.ok) throw new Error("Invalid credentials");
        return r.json();
    });
    localStorage.setItem("odyssey_token", data.access_token);
    return data;
}

export async function register(email: string, password: string) {
    return request("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, role: "doctor" }),
    });
}

/* ── Cases ─────────────────────────────────────────────────── */
export const getCases = () => request<{ cases: import("@/types/api").Case[] }>("/cases");

export const getCase = (id: number) =>
    request<{ case: import("@/types/api").Case }>(`/cases/${id}`);

export const createCase = (data: import("@/types/api").CaseCreate) =>
    request<{ case_id: number }>("/cases", {
        method: "POST",
        body: JSON.stringify(data),
    });

/* ── Normalize / Analyze ──────────────────────────────────── */
export const normalize = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/normalize`, { method: "POST" });

export const analyze = (id: number, include = "") =>
    request<Record<string, unknown>>(
        `/cases/${id}/analyze${include ? `?include=${include}` : ""}`,
        { method: "POST", body: JSON.stringify({ force: true }) }
    );

export const getAnalysis = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/analysis`);

/* ── Phase 5A ─────────────────────────────────────────────── */
export const postEstimate = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/estimate`, { method: "POST" });
export const getEstimate = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/estimate`);

export const postSpotlight = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/spotlight`, { method: "POST" });
export const getSpotlight = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/spotlight`);

/* ── Phase 6 ──────────────────────────────────────────────── */
export const postTrustReport = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/trust_report`, { method: "POST" });
export const getTrustReport = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/trust_report`);

/* ── Phase 7 ──────────────────────────────────────────────── */
export const uploadAudio = (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Record<string, unknown>>(`/cases/${id}/audio`, {
        method: "POST",
        body: form,
    });
};

export const transcribe = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/transcribe`, { method: "POST" });

export const captionImages = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/caption_images`, { method: "POST" });

export const uploadFile = (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Record<string, unknown>>(`/cases/${id}/files`, {
        method: "POST",
        body: form,
    });
};

/* ── Phase 8 ──────────────────────────────────────────────── */
export const ingestAll = (id: number) =>
    request<Record<string, unknown>>(`/cases/${id}/ingest_all`, { method: "POST" });

export const getJobStatus = (id: number) =>
    request<Record<string, unknown>>(`/cases/jobs/${id}`);

export const getMetrics = () =>
    request<import("@/types/api").Metrics>("/metrics");
