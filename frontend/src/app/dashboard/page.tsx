"use client";

import { useState } from "react";
import { useCases, useCreateCase } from "@/hooks/useCases";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    FileText, Plus, ArrowRight, Loader2, Clock, Search, User,
    Stethoscope, ChevronRight, FolderOpen, AlertCircle
} from "lucide-react";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter,
    DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export default function DashboardPage() {
    const { data, isLoading, error } = useCases();
    const createCase = useCreateCase();
    const [isCreating, setIsCreating] = useState(false);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [formData, setFormData] = useState({
        title: "", age: "", sex: "female", chief_complaint: "",
    });

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsCreating(true);
        try {
            const res = await createCase.mutateAsync({
                title: formData.title || "New Case Assessment",
                age: formData.age ? parseInt(formData.age) : undefined,
                sex: formData.sex,
                chief_complaint: formData.chief_complaint || "TBD",
            });
            window.location.href = `/cases/${res.case_id}`;
        } catch (e) {
            console.error(e);
            setIsCreating(false);
        }
    };

    if (isLoading) return (
        <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-slate-400">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                <p className="text-sm">Loading cases...</p>
            </div>
        </div>
    );
    if (error) return (
        <div className="p-8 flex items-center gap-3 text-red-500">
            <AlertCircle className="h-5 w-5" />
            Failed to load cases
        </div>
    );

    const cases = (data?.cases || []).filter((c: any) =>
        !searchQuery || c.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.chief_complaint?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const allCases = data?.cases || [];

    return (
        <div className="flex flex-col h-full bg-slate-50">
            {/* Header */}
            <div className="bg-white border-b px-8 py-5">
                <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Active Cases</h1>
                        <p className="text-slate-500 text-sm mt-0.5">
                            {allCases.length} {allCases.length === 1 ? "case" : "cases"} in your workspace
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                            <input
                                type="text"
                                placeholder="Search cases..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="h-9 pl-9 pr-4 rounded-lg border border-slate-200 bg-slate-50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all w-56"
                            />
                        </div>
                        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                            <DialogTrigger asChild>
                                <Button className="gap-2 bg-blue-600 hover:bg-blue-700 h-9 text-sm font-semibold shadow-sm">
                                    <Plus className="h-4 w-4" />
                                    New Case
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="sm:max-w-[440px]">
                                <form onSubmit={handleCreate}>
                                    <DialogHeader>
                                        <DialogTitle>Create New Case</DialogTitle>
                                        <DialogDescription>
                                            Enter basic patient details to start a new clinical analysis.
                                        </DialogDescription>
                                    </DialogHeader>
                                    <div className="grid gap-4 py-4">
                                        <div className="grid gap-2">
                                            <Label htmlFor="title">Case Title / Identifier</Label>
                                            <Input id="title" placeholder="e.g. 58yo M Chest Pain" value={formData.title}
                                                onChange={(e) => setFormData({ ...formData, title: e.target.value })} required />
                                        </div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="grid gap-2">
                                                <Label htmlFor="age">Age (years)</Label>
                                                <Input id="age" type="number" placeholder="45" value={formData.age}
                                                    onChange={(e) => setFormData({ ...formData, age: e.target.value })} />
                                            </div>
                                            <div className="grid gap-2">
                                                <Label htmlFor="sex">Biological Sex</Label>
                                                <select id="sex"
                                                    className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                    value={formData.sex}
                                                    onChange={(e) => setFormData({ ...formData, sex: e.target.value })}>
                                                    <option value="female">Female</option>
                                                    <option value="male">Male</option>
                                                    <option value="other">Other</option>
                                                </select>
                                            </div>
                                        </div>
                                        <div className="grid gap-2">
                                            <Label htmlFor="chief_complaint">Chief Complaint</Label>
                                            <Textarea id="chief_complaint" placeholder="Brief description of primary symptoms..."
                                                value={formData.chief_complaint}
                                                onChange={(e) => setFormData({ ...formData, chief_complaint: e.target.value })} required />
                                        </div>
                                    </div>
                                    <DialogFooter>
                                        <Button type="submit" disabled={isCreating} className="bg-blue-600 hover:bg-blue-700">
                                            {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                            Create Case
                                        </Button>
                                    </DialogFooter>
                                </form>
                            </DialogContent>
                        </Dialog>
                    </div>
                </div>
            </div>

            {/* Cases Grid */}
            <div className="flex-1 overflow-auto px-8 py-6">
                <div className="max-w-6xl mx-auto">
                    {cases.length === 0 && allCases.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-24 text-center">
                            <div className="bg-blue-50 rounded-full p-6 mb-4">
                                <FolderOpen className="h-10 w-10 text-blue-400" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-900 mb-1">No cases yet</h3>
                            <p className="text-slate-500 text-sm mb-6 max-w-sm">
                                Create your first case to begin clinical analysis with AI.
                            </p>
                            <Button onClick={() => setIsDialogOpen(true)} className="bg-blue-600 hover:bg-blue-700 gap-2">
                                <Plus className="h-4 w-4" /> Create First Case
                            </Button>
                        </div>
                    ) : cases.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-24 text-center">
                            <Search className="h-10 w-10 text-slate-300 mb-3" />
                            <p className="text-slate-600 font-medium">No cases match your search</p>
                            <p className="text-slate-400 text-sm mt-1">Try a different keyword</p>
                        </div>
                    ) : (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {cases.map((c: any) => (
                                <a
                                    key={c.id}
                                    href={`/cases/${c.id}`}
                                    className="group bg-white rounded-xl border border-slate-200 hover:border-blue-200 hover:shadow-md hover:shadow-blue-50 transition-all flex flex-col overflow-hidden"
                                >
                                    {/* Card header accent */}
                                    <div className="h-1 bg-gradient-to-r from-blue-500 to-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity" />

                                    <div className="p-5 flex-1">
                                        <div className="flex items-start justify-between gap-2 mb-3">
                                            <div className="bg-blue-50 rounded-lg p-2 shrink-0">
                                                <Stethoscope className="h-4 w-4 text-blue-600" />
                                            </div>
                                            <Badge variant="secondary" className="text-[10px] font-semibold shrink-0">
                                                ID #{c.id}
                                            </Badge>
                                        </div>
                                        <h3 className="font-semibold text-slate-900 leading-snug mb-2 group-hover:text-blue-700 transition-colors">
                                            {c.title}
                                        </h3>
                                        <p className="text-sm text-slate-500 line-clamp-2 leading-relaxed">
                                            {c.chief_complaint}
                                        </p>
                                    </div>

                                    <div className="px-5 pb-5 flex items-center justify-between">
                                        <div className="flex items-center gap-3 text-xs text-slate-400">
                                            {c.age && (
                                                <span className="flex items-center gap-1">
                                                    <User className="h-3 w-3" /> {c.age}yo
                                                </span>
                                            )}
                                            {c.sex && (
                                                <span className="capitalize">{c.sex}</span>
                                            )}
                                            <span className="flex items-center gap-1">
                                                <Clock className="h-3 w-3" />
                                                {new Date(c.created_at || Date.now()).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-1 text-xs font-semibold text-blue-600 group-hover:gap-2 transition-all">
                                            Open <ChevronRight className="h-3.5 w-3.5" />
                                        </div>
                                    </div>
                                </a>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
