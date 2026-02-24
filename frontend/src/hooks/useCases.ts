import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCases, getCase, createCase } from "@/lib/api";
import { CaseCreate } from "@/types/api";

export function useCases() {
    return useQuery({
        queryKey: ["cases"],
        queryFn: getCases,
    });
}

export function useCase(id: number) {
    return useQuery({
        queryKey: ["cases", id],
        queryFn: () => getCase(id),
        enabled: !!id,
    });
}

export function useCreateCase() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data: CaseCreate) => createCase(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["cases"] });
        },
    });
}
