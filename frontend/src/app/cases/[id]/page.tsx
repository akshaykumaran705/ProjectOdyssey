"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useCase } from "@/hooks/useCases";
import {
    useCaseAnalysis,
    useCaseEstimate,
    useCaseSpotlight,
    useCaseTrustReport,
    useIngestAll,
} from "@/hooks/useCaseAnalysis";
import { getJobStatus } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { UploadPanel } from "@/components/upload-panel";
import { RadialProgress } from "@/components/ui/radial-progress";
import {
    Loader2, Play, AlertTriangle, ShieldCheck, FileText, List,
    Activity, Search, DollarSign, ActivitySquare, ShieldAlert,
    CheckCircle, XCircle, Info, TrendingUp, Stethoscope, FlaskConical,
    Clock, MapPin
} from "lucide-react";

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Parse key_evidence into clean string[] for display. */
function parseKeyEvidence(ke: any): string[] {
    if (!ke) return [];
    // Case 1: already a plain string array
    if (Array.isArray(ke)) {
        return ke.flatMap((item: any) => {
            if (typeof item === "string") {
                // might be a JSON string like '{"attributed_evidence":[...]}'
                try {
                    const parsed = JSON.parse(item);
                    if (parsed?.attributed_evidence) {
                        return (parsed.attributed_evidence as any[]).map((e: any) => e.text || String(e)).filter(Boolean);
                    }
                    if (parsed?.text) return [parsed.text];
                } catch {
                    return [item];
                }
                return [item];
            }
            if (typeof item === "object" && item !== null) {
                if (item.attributed_evidence) {
                    return (item.attributed_evidence as any[]).map((e: any) => e.text || String(e)).filter(Boolean);
                }
                if (item.text) return [item.text];
                if (item.claim) return [item.claim];
                return [JSON.stringify(item)];
            }
            return [String(item)];
        });
    }
    // Case 2: object with attributed_evidence
    if (typeof ke === "object" && ke !== null) {
        if (ke.attributed_evidence) {
            return (ke.attributed_evidence as any[]).map((e: any) => e.text || String(e)).filter(Boolean);
        }
        if (ke.text) return [ke.text];
        return [JSON.stringify(ke)];
    }
    // Case 3: raw string
    if (typeof ke === "string") {
        try {
            return parseKeyEvidence(JSON.parse(ke));
        } catch {
            return [ke];
        }
    }
    return [];
}

/** Safely convert LLM text that might be concatenated without spaces.
 * e.g. "Severe abdominal painGeneralized weakness" → "Severe abdominal pain. Generalized weakness"
 */
function formatText(s: any): string {
    if (!s) return "";
    const str = typeof s === "string" ? s : String(s);
    // Insert a space before capital letters that follow lowercase or digits (camel-run)
    return str.replace(/([a-z0-9])([A-Z])/g, "$1. $2");
}

/** Likelihood colour helper */
function likelihoodVariant(lh: string): "default" | "secondary" | "outline" {
    const s = (lh || "").toLowerCase();
    if (s.includes("high")) return "default";
    if (s.includes("medium") || s.includes("moderate")) return "secondary";
    return "outline";
}

// ── Page Component ────────────────────────────────────────────────────────────

export default function CaseDetailPage() {
    const params = useParams();
    const caseId = Number(params.id);

    const { data: caseData, isLoading: caseLoading } = useCase(caseId);
    const { data: analysisData, refetch: refetchAnalysis } = useCaseAnalysis(caseId);
    const { data: estimateData, refetch: refetchEstimate } = useCaseEstimate(caseId);
    const { data: spotlightData, refetch: refetchSpotlight } = useCaseSpotlight(caseId);
    const { data: trustData, refetch: refetchTrust } = useCaseTrustReport(caseId);
    const ingestAll = useIngestAll(caseId);

    const [activeTab, setActiveTab] = useState("narrative");
    const [isPolling, setIsPolling] = useState(false);
    const [pollMessage, setPollMessage] = useState("");

    const handleUploadSuccess = async () => {
        await Promise.all([refetchAnalysis(), refetchEstimate(), refetchSpotlight(), refetchTrust()]);
    };

    const handleRunPipeline = async () => {
        try {
            setPollMessage("Starting pipeline...");
            setIsPolling(true);
            const res = await ingestAll.mutateAsync() as any;
            const jobId = res?.job_id;

            if (!jobId) {
                await handleUploadSuccess();
                setIsPolling(false);
                setActiveTab("analysis");
                return;
            }

            const poll = async () => {
                try {
                    const statusRes = await getJobStatus(jobId) as any;
                    if (statusRes.status === "complete") {
                        await handleUploadSuccess();
                        setIsPolling(false);
                        setPollMessage("");
                        setActiveTab("analysis");
                    } else if (statusRes.status === "failed") {
                        alert("Pipeline failed: " + (statusRes.error_message || "Unknown error"));
                        setIsPolling(false);
                        setPollMessage("");
                    } else {
                        const steps = statusRes.meta_data?.steps?.length || 0;
                        setPollMessage(`Running (${steps}/6 steps)...`);
                        setTimeout(poll, 3000);
                    }
                } catch (e) {
                    console.error("Polling error", e);
                    setTimeout(poll, 3000);
                }
            };
            setTimeout(poll, 3000);
        } catch (e) {
            console.error(e);
            setIsPolling(false);
            setPollMessage("");
        }
    };

    if (caseLoading) return (
        <div className="flex h-full items-center justify-center p-8">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
    );
    if (!caseData?.case) return <div className="p-8">Case not found</div>;

    const c = caseData.case;
    const analysis = analysisData?.analysis_data as any;
    const estimate = estimateData?.estimate as any;
    const spotlight = spotlightData?.spotlight as any;
    const trust = trustData?.trust_report as any;
    const structured = analysisData?.structured_case as any;
    const narrative = (analysisData?.narrative as string) || "";

    // Cost fields — backend returns `low_total`/`high_total` and `line_items`
    const costLow = estimate?.low_total ?? estimate?.total_low;
    const costHigh = estimate?.high_total ?? estimate?.total_high;
    const lineItems: any[] = estimate?.line_items ?? estimate?.items ?? [];

    return (
        <div className="flex h-full flex-col lg:flex-row">
            {/* ── Left Sidebar ── */}
            <div className="w-full lg:w-80 border-r bg-white p-6 overflow-y-auto shrink-0 flex flex-col gap-6">
                <div>
                    <Badge variant="secondary" className="mb-2">ID: {c.id}</Badge>
                    <h1 className="text-xl font-bold text-slate-900">{c.title}</h1>
                    {(c.age || c.sex) && (
                        <p className="text-sm text-slate-500 mt-1 capitalize">
                            {c.age ? `${c.age}yo ` : ""}{c.sex || ""}
                        </p>
                    )}
                </div>

                <div className="space-y-4 text-sm">
                    <div>
                        <span className="font-semibold text-slate-900 block mb-1">Chief Complaint</span>
                        <span className="text-slate-600">{c.chief_complaint}</span>
                    </div>
                    {c.history_present_illness && (
                        <div>
                            <span className="font-semibold text-slate-900 block mb-1">History of Present Illness</span>
                            <span className="text-slate-600 line-clamp-4">{c.history_present_illness}</span>
                        </div>
                    )}
                </div>

                <div className="border-t pt-6 space-y-4">
                    <h3 className="font-semibold text-sm text-slate-900">Patient Data</h3>
                    <UploadPanel caseId={caseId} onUploadSuccess={handleUploadSuccess} />
                </div>

                <div className="border-t pt-6 mt-auto">
                    <Button
                        className="w-full gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold"
                        onClick={handleRunPipeline}
                        disabled={ingestAll.isPending || isPolling}
                    >
                        {(ingestAll.isPending || isPolling)
                            ? <Loader2 className="h-4 w-4 animate-spin" />
                            : <Play className="h-4 w-4 fill-current" />}
                        {(ingestAll.isPending || isPolling) ? (pollMessage || "Running Pipeline...") : "Run AI Analysis"}
                    </Button>
                    <p className="text-xs text-slate-400 mt-2 text-center">
                        Extracts PDFs, transcribes audio, captions images, and analyzes case
                    </p>
                </div>
            </div>

            {/* ── Main Content ── */}
            <div className="flex-1 overflow-y-auto bg-slate-50/50 p-6">
                <div className="max-w-5xl mx-auto">
                    {!analysis && !ingestAll.isPending && !isPolling && (
                        <Card className="border-dashed shadow-none bg-blue-50/50 mb-6">
                            <CardContent className="flex flex-col items-center justify-center p-12 text-center space-y-4">
                                <ActivitySquare className="h-12 w-12 text-blue-300" />
                                <div>
                                    <h3 className="text-lg font-semibold text-blue-900">No Analysis Yet</h3>
                                    <p className="text-blue-700/80 mt-1">Upload documents or audio, then click Run AI Analysis</p>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                        <TabsList className="grid grid-cols-3 lg:grid-cols-6 h-auto p-1 bg-white border shadow-sm rounded-lg">
                            <TabsTrigger value="narrative" className="gap-1.5 py-2 text-xs sm:text-sm">
                                <FileText className="h-3.5 w-3.5" /> Narrative
                            </TabsTrigger>
                            <TabsTrigger value="structured" className="gap-1.5 py-2 text-xs sm:text-sm">
                                <List className="h-3.5 w-3.5" /> Structured
                            </TabsTrigger>
                            <TabsTrigger value="analysis" className="gap-1.5 py-2 text-xs sm:text-sm">
                                <Activity className="h-3.5 w-3.5" /> Analysis
                            </TabsTrigger>
                            <TabsTrigger value="spotlight" className="gap-1.5 py-2 text-xs sm:text-sm">
                                <Search className="h-3.5 w-3.5" /> Rare
                            </TabsTrigger>
                            <TabsTrigger value="cost" className="gap-1.5 py-2 text-xs sm:text-sm">
                                <DollarSign className="h-3.5 w-3.5" /> Cost
                            </TabsTrigger>
                            <TabsTrigger value="trust" className="gap-1.5 py-2 text-xs sm:text-sm">
                                <ShieldCheck className="h-3.5 w-3.5" /> Trust
                            </TabsTrigger>
                        </TabsList>

                        {/* ── TAB: Narrative ── */}
                        <TabsContent value="narrative" className="space-y-4 outline-none">
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <FileText className="h-5 w-5 text-slate-500" />
                                        Canonical Narrative
                                    </CardTitle>
                                    <CardDescription>Merged patient story, transcripts, and image findings</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {narrative ? (
                                        <div className="bg-slate-50 border rounded-lg p-5 text-sm text-slate-700 leading-relaxed whitespace-pre-wrap font-sans">
                                            {narrative}
                                        </div>
                                    ) : (
                                        <div className="bg-slate-50 border border-dashed rounded-lg p-10 text-center text-slate-400">
                                            <FileText className="h-8 w-8 mx-auto mb-3 opacity-40" />
                                            <p>No narrative available. Upload a PDF and run the pipeline.</p>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </TabsContent>

                        {/* ── TAB: Structured ── */}
                        <TabsContent value="structured" className="space-y-4 outline-none">
                            {!structured ? (
                                <EmptyState icon={<List className="h-8 w-8 opacity-40" />} message="No structured data. Run the AI pipeline first." />
                            ) : (
                                <div className="space-y-4">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <StructuredCard title="Symptoms" icon={<Stethoscope className="h-4 w-4 text-blue-500" />} items={structured?.symptoms} emptyText="No symptoms extracted" />
                                        <StructuredCard title="Abnormal Labs / Vitals" icon={<FlaskConical className="h-4 w-4 text-amber-500" />}
                                            items={(structured?.abnormal_labs || []).map((lab: any) =>
                                                typeof lab === "string" ? lab
                                                    : `${lab.name || lab.test || ""}: ${lab.value || lab.result || ""} ${lab.flag ? `(${lab.flag})` : ""}`
                                            )}
                                            emptyText="No abnormal labs extracted" />
                                    </div>

                                    {/* Red Flags */}
                                    {(structured?.red_flags?.length > 0) && (
                                        <Card className="border-red-100 bg-red-50/30">
                                            <CardHeader className="pb-2 flex flex-row items-center gap-2">
                                                <AlertTriangle className="h-4 w-4 text-red-500" />
                                                <CardTitle className="text-base text-red-800">Red Flags</CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ul className="space-y-1.5">
                                                    {structured.red_flags.map((flag: string, i: number) => (
                                                        <li key={i} className="flex items-start gap-2 text-sm text-red-700 font-medium">
                                                            <span className="text-red-500 mt-0.5">⚠</span> {flag}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </CardContent>
                                        </Card>
                                    )}

                                    {/* Timeline */}
                                    {structured?.timeline && (
                                        <Card>
                                            <CardHeader className="pb-2 flex flex-row items-center gap-2">
                                                <Clock className="h-4 w-4 text-slate-500" />
                                                <CardTitle className="text-base">Timeline</CardTitle>
                                            </CardHeader>
                                            <CardContent className="text-sm text-slate-600 space-y-1">
                                                {Object.entries(structured.timeline).map(([k, v]) => (
                                                    <div key={k} className="flex gap-3">
                                                        <span className="font-medium capitalize text-slate-700 w-24 shrink-0">{k}:</span>
                                                        <span>{String(v)}</span>
                                                    </div>
                                                ))}
                                            </CardContent>
                                        </Card>
                                    )}

                                    {/* Past Medical History */}
                                    {structured?.past_medical_history?.length > 0 && (
                                        <StructuredCard title="Past Medical History" icon={<Info className="h-4 w-4 text-slate-400" />} items={structured.past_medical_history} />
                                    )}

                                    {/* Medications */}
                                    {structured?.current_medications?.length > 0 && (
                                        <StructuredCard title="Current Medications" icon={<Info className="h-4 w-4 text-slate-400" />} items={structured.current_medications} />
                                    )}
                                </div>
                            )}
                        </TabsContent>

                        {/* ── TAB: Analysis ── */}
                        <TabsContent value="analysis" className="space-y-6 outline-none">
                            {!analysis ? (
                                <EmptyState icon={<Activity className="h-8 w-8 opacity-40" />} message="No analysis yet. Run the AI pipeline first." />
                            ) : (
                                <>
                                    {/* Triage Banner */}
                                    {analysis.triage_recommendation && (
                                        <div className="bg-blue-50 border border-blue-200 text-blue-900 px-5 py-4 rounded-xl flex gap-3 items-start">
                                            <AlertTriangle className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                                            <div>
                                                <h4 className="font-semibold text-sm mb-0.5">Triage Recommendation</h4>
                                                <p className="text-sm">{analysis.triage_recommendation}</p>
                                            </div>
                                        </div>
                                    )}

                                    {/* Differential Diagnosis */}
                                    <div className="space-y-3">
                                        <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                                            <TrendingUp className="h-4 w-4 text-blue-500" /> Differential Diagnosis
                                        </h3>
                                        {(analysis.top_differentials || []).map((ddx: any, i: number) => {
                                            const evidence = parseKeyEvidence(ddx.key_evidence);
                                            return (
                                                <Card key={i} className={`overflow-hidden ${i === 0 ? "border-blue-200 shadow-sm" : ""}`}>
                                                    <div className={`px-5 py-4 flex items-start justify-between gap-4 border-b ${i === 0 ? "bg-blue-50/50" : "bg-slate-50/50"}`}>
                                                        <div className="flex items-start gap-3">
                                                            <span className={`rounded-full w-7 h-7 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 ${i === 0 ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-600"}`}>
                                                                {i + 1}
                                                            </span>
                                                            <div>
                                                                <h4 className="font-bold text-slate-900 text-base">{ddx.name}</h4>
                                                                {ddx.rationale && <p className="text-sm text-slate-500 mt-0.5">{ddx.rationale}</p>}
                                                            </div>
                                                        </div>
                                                        <Badge variant={likelihoodVariant(ddx.likelihood)} className="shrink-0 mt-0.5 capitalize">
                                                            {ddx.likelihood || "Unknown"}
                                                        </Badge>
                                                    </div>
                                                    <CardContent className="pt-4 pb-4">
                                                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Key Evidence</p>
                                                        {evidence.length > 0 ? (
                                                            <ul className="space-y-1.5">
                                                                {evidence.map((ev, j) => (
                                                                    <li key={j} className="flex items-start gap-2 text-sm text-slate-700">
                                                                        <span className="text-blue-400 shrink-0 mt-0.5">•</span>
                                                                        {ev}
                                                                    </li>
                                                                ))}
                                                            </ul>
                                                        ) : (
                                                            <p className="text-sm text-slate-400 italic">No evidence listed</p>
                                                        )}

                                                        {/* Recommended next steps per dx */}
                                                        {ddx.recommended_next_steps?.length > 0 && (
                                                            <div className="mt-3 pt-3 border-t">
                                                                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Next Steps</p>
                                                                <ul className="space-y-1">
                                                                    {ddx.recommended_next_steps.map((step: any, j: number) => (
                                                                        <li key={j} className="flex items-center gap-2 text-sm text-slate-600">
                                                                            <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold uppercase ${step.priority === "stat" ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-500"}`}>
                                                                                {step.priority || "routine"}
                                                                            </span>
                                                                            {step.action || step}
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        )}
                                                    </CardContent>
                                                </Card>
                                            );
                                        })}
                                    </div>

                                    {/* Missing Info */}
                                    {analysis.missing_info?.length > 0 && (
                                        <Card className="border-amber-100 bg-amber-50/30">
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-sm font-semibold text-amber-800 flex items-center gap-2">
                                                    <Info className="h-4 w-4" /> Missing Information Needed to Confirm
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ul className="space-y-1.5">
                                                    {analysis.missing_info.map((info: string, i: number) => (
                                                        <li key={i} className="text-sm text-amber-800 flex items-start gap-2">
                                                            <span className="mt-0.5 text-amber-500 shrink-0">–</span> {info}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </CardContent>
                                        </Card>
                                    )}

                                    {/* Top-level recommended next steps */}
                                    {Array.isArray(analysis.recommended_next_steps) && analysis.recommended_next_steps.length > 0 && (
                                        <Card>
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-base">Recommended Next Steps</CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ul className="space-y-2">
                                                    {analysis.recommended_next_steps.map((step: any, i: number) => (
                                                        <li key={i} className="flex items-center gap-3 text-sm text-slate-700">
                                                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase shrink-0 ${step.priority === "stat" ? "bg-red-100 text-red-700" : step.priority === "today" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
                                                                {step.priority || "routine"}
                                                            </span>
                                                            <span>{step.action || step}</span>
                                                            {step.rationale && <span className="text-slate-400 text-xs">— {step.rationale}</span>}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </CardContent>
                                        </Card>
                                    )}
                                </>
                            )}
                        </TabsContent>

                        {/* ── TAB: Rare Spotlight ── */}
                        <TabsContent value="spotlight" className="space-y-6 outline-none">
                            {!spotlight ? (
                                <EmptyState icon={<Search className="h-8 w-8 opacity-40" />} message="No rare disease spotlight data yet. Run the pipeline first." />
                            ) : (
                                <>
                                    {/* Delay Risk Score */}
                                    <Card className="bg-gradient-to-br from-purple-50 to-indigo-50 border-purple-100 overflow-hidden">
                                        <CardContent className="p-6">
                                            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
                                                {/* Radial */}
                                                <div className="shrink-0 flex flex-col items-center gap-2">
                                                    <RadialProgress
                                                        value={Math.min((spotlight.diagnostic_delay_risk || 0), 100)}
                                                        size={96}
                                                        strokeWidth={9}
                                                        indicatorClassName="text-purple-600"
                                                        trackClassName="text-purple-200"
                                                    >
                                                        <span className="text-xl font-extrabold text-purple-900">
                                                            {spotlight.diagnostic_delay_risk ?? 0}
                                                        </span>
                                                    </RadialProgress>
                                                    <span className="text-[10px] font-semibold text-purple-500 uppercase tracking-wider">Risk Score</span>
                                                </div>
                                                {/* Text */}
                                                <div className="flex-1 min-w-0">
                                                    <h3 className="text-purple-900 font-bold text-lg">Diagnostic Delay Risk</h3>
                                                    <p className="text-purple-600 text-sm mt-1">
                                                        Indicates the probability of this patient experiencing a prolonged diagnostic odyssey.
                                                    </p>
                                                    {(spotlight.delay_reasoning || []).length > 0 && (
                                                        <ul className="mt-3 space-y-1">
                                                            {spotlight.delay_reasoning.map((r: string, i: number) => (
                                                                <li key={i} className="text-xs text-purple-700 flex items-start gap-1.5">
                                                                    <span className="mt-1 shrink-0 text-purple-400">›</span>
                                                                    {formatText(r)}
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    )}
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    {/* Candidates */}
                                    {spotlight.candidates?.length > 0 ? (
                                        <div className="space-y-4">
                                            <h3 className="text-base font-semibold text-slate-900">Rare Disease Candidates</h3>
                                            {spotlight.candidates.map((cand: any, i: number) => (
                                                <Card key={i} className="border-purple-100 overflow-hidden">
                                                    <div className="bg-purple-50/60 px-6 py-4 flex justify-between items-center border-b border-purple-100">
                                                        <h4 className="font-bold text-lg text-purple-900">{cand.disease || cand.name}</h4>
                                                        <Badge variant="outline" className="text-purple-700 border-purple-200 bg-white capitalize">
                                                            {cand.likelihood} Match
                                                        </Badge>
                                                    </div>
                                                    <CardContent className="p-6 grid md:grid-cols-2 gap-6">
                                                        <div className="space-y-4">
                                                            <div>
                                                                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Why This Fits</p>
                                                                <p className="text-sm text-slate-700 leading-relaxed">
                                                                    {formatText(cand.why_this_fits || "")}
                                                                </p>
                                                            </div>
                                                            <div>
                                                                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Supporting Evidence</p>
                                                                <ul className="space-y-1.5">
                                                                    {(cand.supporting_evidence || []).map((e: string, j: number) => (
                                                                        <li key={j} className="flex items-start gap-2 text-sm text-slate-600">
                                                                            <span className="text-purple-400 mt-0.5 shrink-0">•</span>
                                                                            {formatText(e)}
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        </div>
                                                        <div className="bg-slate-50 rounded-xl p-5 space-y-4">
                                                            <div>
                                                                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Confirmatory Tests</p>
                                                                <ul className="space-y-1.5">
                                                                    {(cand.confirmatory_tests || []).map((t: string, j: number) => (
                                                                        <li key={j} className="flex items-start gap-2 text-sm text-slate-800 font-medium">
                                                                            <span className="text-green-500 mt-0.5 shrink-0">✓</span> {t}
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                            {cand.specialist_referral && (
                                                                <div className="border-t pt-4">
                                                                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Specialist Referral</p>
                                                                    <div className="flex items-center gap-2 mt-2">
                                                                        <span className="bg-blue-100 text-blue-700 text-sm font-semibold px-3 py-1.5 rounded-lg">
                                                                            {cand.specialist_referral}
                                                                        </span>
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </CardContent>
                                                </Card>
                                            ))}
                                        </div>
                                    ) : (
                                        <Card>
                                            <CardContent className="p-8 text-center text-slate-500">
                                                <Search className="h-8 w-8 mx-auto mb-3 opacity-30" />
                                                <p className="font-medium">No rare disease candidates identified</p>
                                                <p className="text-sm mt-1">The primary differentials appear to be common conditions.</p>
                                            </CardContent>
                                        </Card>
                                    )}

                                    {/* Next Best Actions */}
                                    {spotlight.next_best_actions?.length > 0 && (
                                        <Card>
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-base">Recommended Next Actions</CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ul className="space-y-2">
                                                    {spotlight.next_best_actions.map((action: string, i: number) => (
                                                        <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                                                            <span className="text-purple-500 shrink-0 mt-0.5">→</span> {action}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </CardContent>
                                        </Card>
                                    )}
                                </>
                            )}
                        </TabsContent>

                        {/* ── TAB: Cost ── */}
                        <TabsContent value="cost" className="space-y-6 outline-none">
                            {!estimate ? (
                                <EmptyState icon={<DollarSign className="h-8 w-8 opacity-40" />} message="No cost estimate yet. Run the AI pipeline first." />
                            ) : (
                                <>
                                    {/* Summary Banner */}
                                    <Card className="bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-100 overflow-hidden">
                                        <CardContent className="p-8 text-center">
                                            <p className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-3">Estimated Diagnostic Cost</p>
                                            <div className="text-5xl font-extrabold text-emerald-900 tracking-tight">
                                                {costLow != null && costHigh != null
                                                    ? `$${costLow.toLocaleString()} – $${costHigh.toLocaleString()}`
                                                    : "Not Available"}
                                            </div>
                                            <p className="text-sm text-emerald-600 mt-3 max-w-lg mx-auto">
                                                Based on {lineItems.length} recommended {lineItems.length === 1 ? "test" : "tests"} and procedures derived from the differential diagnosis.
                                            </p>
                                            {estimate.region && (
                                                <p className="text-xs text-emerald-500 mt-1 flex items-center justify-center gap-1">
                                                    <MapPin className="h-3 w-3" /> {estimate.region}
                                                </p>
                                            )}
                                            {estimate.confidence && (
                                                <Badge variant="outline" className="mt-3 border-emerald-200 text-emerald-700 capitalize">
                                                    {estimate.confidence} confidence
                                                </Badge>
                                            )}
                                        </CardContent>
                                    </Card>

                                    {/* Line Items Table */}
                                    {lineItems.length > 0 ? (
                                        <Card>
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-base">Diagnostic Tests Breakdown</CardTitle>
                                                <CardDescription>US cash-pay estimates. Actual costs vary by facility and insurance.</CardDescription>
                                            </CardHeader>
                                            <div className="overflow-x-auto">
                                                <table className="w-full text-sm text-left">
                                                    <thead className="bg-slate-50 border-y text-slate-500 uppercase text-xs">
                                                        <tr>
                                                            <th className="px-6 py-3 font-semibold">Test / Procedure</th>
                                                            <th className="px-6 py-3 font-semibold">CPT Code</th>
                                                            <th className="px-6 py-3 font-semibold text-right">Low</th>
                                                            <th className="px-6 py-3 font-semibold text-right">High</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y text-slate-700">
                                                        {lineItems.map((item: any, i: number) => (
                                                            <tr key={i} className="hover:bg-slate-50 transition-colors">
                                                                <td className="px-6 py-4 font-medium capitalize">{item.item}</td>
                                                                <td className="px-6 py-4 text-slate-400 font-mono text-xs">{item.cpt_or_code || "–"}</td>
                                                                <td className="px-6 py-4 text-right text-emerald-700">${(item.low ?? 0).toLocaleString()}</td>
                                                                <td className="px-6 py-4 text-right font-semibold">${(item.high ?? 0).toLocaleString()}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                    {lineItems.length > 1 && (
                                                        <tfoot className="bg-emerald-50 border-t-2 border-emerald-100">
                                                            <tr>
                                                                <td className="px-6 py-4 font-bold text-slate-900" colSpan={2}>Total</td>
                                                                <td className="px-6 py-4 text-right font-bold text-emerald-700">${(costLow ?? 0).toLocaleString()}</td>
                                                                <td className="px-6 py-4 text-right font-bold">${(costHigh ?? 0).toLocaleString()}</td>
                                                            </tr>
                                                        </tfoot>
                                                    )}
                                                </table>
                                            </div>
                                        </Card>
                                    ) : (
                                        <Card>
                                            <CardContent className="p-6 text-sm text-slate-500">
                                                No line items available. The LLM did not identify specific testable procedures from the differential.
                                            </CardContent>
                                        </Card>
                                    )}

                                    {/* Assumptions */}
                                    {estimate.assumptions?.length > 0 && (
                                        <Card className="border-slate-100 bg-slate-50/50">
                                            <CardHeader className="pb-1">
                                                <CardTitle className="text-sm text-slate-500">Pricing Assumptions</CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ul className="space-y-1">
                                                    {estimate.assumptions.map((a: string, i: number) => (
                                                        <li key={i} className="text-xs text-slate-500 flex items-start gap-2">
                                                            <span className="mt-0.5 shrink-0">·</span> {a}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </CardContent>
                                        </Card>
                                    )}

                                    {/* Exclusions */}
                                    {estimate.exclusions?.length > 0 && (
                                        <Card className="border-amber-100 bg-amber-50/30">
                                            <CardHeader className="pb-1">
                                                <CardTitle className="text-sm text-amber-700 flex items-center gap-2">
                                                    <Info className="h-3.5 w-3.5" /> What's Not Included
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ul className="space-y-1">
                                                    {estimate.exclusions.map((e: string, i: number) => (
                                                        <li key={i} className="text-xs text-amber-700 flex items-start gap-2">
                                                            <span className="mt-0.5 shrink-0">×</span> {e}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </CardContent>
                                        </Card>
                                    )}
                                </>
                            )}
                        </TabsContent>

                        {/* ── TAB: Trust Report ── */}
                        <TabsContent value="trust" className="space-y-6 outline-none">
                            {!trust ? (
                                <EmptyState icon={<ShieldCheck className="h-8 w-8 opacity-40" />} message="No trust report yet. Run the AI pipeline first." />
                            ) : (
                                <>
                                    {/* Summary Row */}
                                    <div className="grid md:grid-cols-3 gap-4">
                                        <Card className="md:col-span-1">
                                            <CardContent className="p-6 flex flex-col items-center justify-center text-center gap-3">
                                                <RadialProgress
                                                    value={(trust.overall_support_ratio || 0) * 100}
                                                    indicatorClassName={trust.status === "ok" ? "text-green-500" : trust.status === "warn" ? "text-amber-500" : "text-red-500"}
                                                />
                                                <div>
                                                    <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Evidence Grounding</p>
                                                    <p className="text-3xl font-bold text-slate-900 mt-1">{Math.round((trust.overall_support_ratio || 0) * 100)}%</p>
                                                    <Badge
                                                        className="mt-2 uppercase"
                                                        variant={trust.status === "ok" ? "default" : trust.status === "warn" ? "secondary" : "destructive"}
                                                    >
                                                        {trust.status}
                                                    </Badge>
                                                </div>
                                            </CardContent>
                                        </Card>

                                        <div className="md:col-span-2 grid grid-cols-3 gap-4">
                                            <StatCard label="Total Claims" value={trust.stats?.total_claims ?? "–"} />
                                            <StatCard label="Supported" value={trust.stats?.supported_claims ?? "–"} color="text-green-600" />
                                            <StatCard label="Unsupported" value={trust.stats?.unsupported_claims ?? "–"} color={trust.stats?.unsupported_claims > 0 ? "text-amber-600" : "text-slate-900"} />
                                            <StatCard label="Avg Confidence" value={`${trust.overall_confidence ?? "–"}/100`} />
                                            <StatCard label="Safety Flags" value={trust.stats?.safety_flags_total ?? "–"} color={trust.stats?.safety_flags_total > 0 ? "text-red-600" : "text-slate-900"} />
                                            <StatCard label="Critical Flags" value={trust.stats?.critical_flags ?? "–"} color={trust.stats?.critical_flags > 0 ? "text-red-700" : "text-slate-900"} />
                                        </div>
                                    </div>

                                    {/* Global Warnings */}
                                    {trust.global_warnings?.length > 0 && (
                                        <Card className="border-amber-200 bg-amber-50">
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-amber-800 text-base flex items-center gap-2">
                                                    <AlertTriangle className="h-4 w-4" /> Warnings
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ul className="space-y-2">
                                                    {trust.global_warnings.map((w: string, i: number) => (
                                                        <li key={i} className="text-sm text-amber-800 flex items-start gap-2">
                                                            <span className="mt-0.5 shrink-0">⚠</span> {w}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </CardContent>
                                        </Card>
                                    )}

                                    {/* Safety Flags */}
                                    {trust.safety_flags?.length > 0 && (
                                        <Card className="border-red-200 bg-red-50">
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-red-800 text-base flex items-center gap-2">
                                                    <ShieldAlert className="h-4 w-4" /> Clinical Safety Alerts
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ul className="space-y-3">
                                                    {trust.safety_flags.map((flag: any, i: number) => (
                                                        <li key={i} className="bg-white rounded-lg border border-red-100 p-4">
                                                            <div className="flex justify-between items-start mb-1">
                                                                <span className="font-bold text-red-700">{flag.flag}</span>
                                                                <Badge variant="destructive" className="uppercase text-[10px] ml-2 shrink-0">{flag.severity}</Badge>
                                                            </div>
                                                            {flag.triggered_by?.length > 0 && (
                                                                <p className="text-xs text-slate-500 mb-1">Triggered by: {flag.triggered_by.join(", ")}</p>
                                                            )}
                                                            {flag.recommendation && (
                                                                <p className="text-sm font-medium text-slate-800 mt-1">→ {flag.recommendation}</p>
                                                            )}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </CardContent>
                                        </Card>
                                    )}

                                    {/* Diagnosis Evidence Traceability */}
                                    <div>
                                        <h3 className="text-base font-semibold text-slate-900 mb-3">Evidence Traceability</h3>
                                        <div className="space-y-4">
                                            {(trust.diagnoses || []).map((dx: any, i: number) => (
                                                <Card key={i} className="overflow-hidden">
                                                    <div className="bg-slate-50 px-5 py-3 border-b flex items-center justify-between">
                                                        <h4 className="font-bold text-slate-900">{dx.diagnosis}</h4>
                                                        <div className="flex items-center gap-3">
                                                            <span className="text-xs text-slate-500">
                                                                Confidence: <strong className="text-slate-800">{dx.confidence_score}/100</strong>
                                                            </span>
                                                            <Badge
                                                                className="uppercase text-[10px]"
                                                                variant={dx.confidence_level === "high" ? "default" : dx.confidence_level === "medium" ? "secondary" : "destructive"}
                                                            >
                                                                {dx.confidence_level}
                                                            </Badge>
                                                        </div>
                                                    </div>
                                                    <div className="divide-y">
                                                        {(dx.evidence_links || []).map((link: any, j: number) => (
                                                            <div key={j} className="px-5 py-3 flex items-start gap-3">
                                                                {link.supported
                                                                    ? <CheckCircle className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
                                                                    : <XCircle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />}
                                                                <div>
                                                                    <p className="text-sm font-medium text-slate-900">{link.claim}</p>
                                                                    {link.supported && link.source_path && (
                                                                        <p className="text-xs text-blue-500 mt-0.5 font-mono">{link.source_path}</p>
                                                                    )}
                                                                    {!link.supported && link.reason && (
                                                                        <p className="text-xs text-amber-600 mt-0.5">{link.reason}</p>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </Card>
                                            ))}
                                        </div>
                                    </div>
                                </>
                            )}
                        </TabsContent>
                    </Tabs>
                </div>
            </div>
        </div>
    );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function EmptyState({ icon, message }: { icon: React.ReactNode; message: string }) {
    return (
        <Card className="border-dashed">
            <CardContent className="p-12 flex flex-col items-center justify-center text-center text-slate-400 gap-3">
                {icon}
                <p className="text-sm">{message}</p>
            </CardContent>
        </Card>
    );
}

function StructuredCard({ title, icon, items, emptyText }: {
    title: string;
    icon?: React.ReactNode;
    items?: string[];
    emptyText?: string;
}) {
    return (
        <Card>
            <CardHeader className="pb-2 flex flex-row items-center gap-2">
                {icon}
                <CardTitle className="text-base">{title}</CardTitle>
            </CardHeader>
            <CardContent>
                {items?.length ? (
                    <ul className="space-y-1.5">
                        {items.map((s, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                                <span className="text-slate-300 mt-0.5 shrink-0">•</span> {s}
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="text-sm text-slate-400 italic">{emptyText || "None"}</p>
                )}
            </CardContent>
        </Card>
    );
}

function StatCard({ label, value, color = "text-slate-900" }: { label: string; value: any; color?: string }) {
    return (
        <Card>
            <CardContent className="p-4 text-center">
                <p className={`text-2xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-slate-500 mt-1">{label}</p>
            </CardContent>
        </Card>
    );
}
