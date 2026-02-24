import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAnalysis, getEstimate, getSpotlight, getTrustReport, ingestAll, analyze } from "@/lib/api";

export function useCaseAnalysis(caseId: number) {
    return useQuery({
        queryKey: ["case", caseId, "analysis"],
        queryFn: () => getAnalysis(caseId),
        enabled: !!caseId,
        retry: false,
    });
}

export function useCaseEstimate(caseId: number) {
    return useQuery({
        queryKey: ["case", caseId, "estimate"],
        queryFn: () => getEstimate(caseId),
        enabled: !!caseId,
        retry: false,
    });
}

export function useCaseSpotlight(caseId: number) {
    return useQuery({
        queryKey: ["case", caseId, "spotlight"],
        queryFn: () => getSpotlight(caseId),
        enabled: !!caseId,
        retry: false,
    });
}

export function useCaseTrustReport(caseId: number) {
    return useQuery({
        queryKey: ["case", caseId, "trust_report"],
        queryFn: () => getTrustReport(caseId),
        enabled: !!caseId,
        retry: false,
    });
}

export function useIngestAll(caseId: number) {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: () => ingestAll(caseId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
        },
    });
}
