"use client";

import { useQuery } from "@tanstack/react-query";
import { getMetrics } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Activity, Database, CheckCircle, Clock } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function MetricsPage() {
    const { data: metrics, isLoading, error } = useQuery({
        queryKey: ["metrics"],
        queryFn: getMetrics,
        refetchInterval: 5000,
    });

    if (isLoading) return <div className="p-8 text-center text-slate-500">Loading metrics...</div>;
    if (error || !metrics) return <div className="p-8 text-red-500">Failed to load metrics</div>;

    const latencyData = [
        { name: "PDF Extract", ms: metrics.latency?.avg_pdf_extraction_ms || 0 },
        { name: "Normalize", ms: metrics.latency?.avg_normalization_ms || 0 },
        { name: "Analysis", ms: metrics.latency?.avg_analysis_ms || 0 },
        { name: "Spotlight", ms: metrics.latency?.avg_spotlight_ms || 0 },
        { name: "Cost", ms: metrics.latency?.avg_cost_estimate_ms || 0 },
        { name: "Trust", ms: metrics.latency?.avg_trust_ms || 0 },
    ].filter(d => d.ms > 0);

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-slate-950">System Metrics</h1>
                <p className="text-slate-500 flex items-center gap-2 mt-1">
                    <span className="flex h-2 w-2 rounded-full bg-green-500"></span>
                    System Operational • <i>Live Updates</i>
                </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Cases</CardTitle>
                        <Database className="h-4 w-4 text-slate-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{metrics.counts.total_cases}</div>
                        <p className="text-xs text-slate-500 mt-1">Stored in database</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Pipeline Jobs</CardTitle>
                        <Activity className="h-4 w-4 text-slate-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{metrics.jobs.total}</div>
                        <p className="text-xs text-slate-500 mt-1">{metrics.jobs.complete} completed, {metrics.jobs.failed} failed</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">LLM Cache Hit Rate</CardTitle>
                        <CheckCircle className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{(metrics.cache.cache_hit_rate * 100).toFixed(0)}%</div>
                        <p className="text-xs text-slate-500 mt-1">Saved {metrics.cache.cache_hits} LLM calls</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg Analysis Latency</CardTitle>
                        <Clock className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{(metrics.latency.avg_analysis_ms / 1000).toFixed(1)}s</div>
                        <p className="text-xs text-slate-500 mt-1">MedGemma completion time</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
                <Card className="col-span-2">
                    <CardHeader>
                        <CardTitle>Pipeline Stage Latency (ms)</CardTitle>
                    </CardHeader>
                    <CardContent className="h-80">
                        {latencyData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={latencyData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                                    <XAxis dataKey="name" axisLine={false} tickLine={false} />
                                    <YAxis axisLine={false} tickLine={false} />
                                    <Tooltip
                                        cursor={{ fill: '#f8fafc' }}
                                        contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                    />
                                    <Bar dataKey="ms" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="h-full flex items-center justify-center text-slate-400">Not enough data for latency charts</div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
