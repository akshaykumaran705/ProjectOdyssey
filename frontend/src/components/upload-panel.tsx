"use client";

import { useState } from "react";
import { useDropzone } from "react-dropzone";
import { uploadFile, uploadAudio, transcribe, captionImages } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { FileUp, FileAudio, FileImage, Loader2, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";

export function UploadPanel({ caseId, onUploadSuccess }: { caseId: number; onUploadSuccess: () => void }) {
    const [loadingAudio, setLoadingAudio] = useState(false);
    const [loadingImage, setLoadingImage] = useState(false);
    const [loadingPdf, setLoadingPdf] = useState(false);
    const [message, setMessage] = useState("");

    const handleUpload = async (files: File[], type: "pdf" | "audio" | "image") => {
        if (!files || files.length === 0) return;
        const file = files[0];

        try {
            setMessage(`Uploading ${file.name}...`);
            if (type === "audio") {
                setLoadingAudio(true);
                await uploadAudio(caseId, file);
                setMessage("Transcribing audio...");
                await transcribe(caseId);
            } else if (type === "image") {
                setLoadingImage(true);
                await uploadFile(caseId, file);
                setMessage("Captioning image...");
                await captionImages(caseId);
            } else {
                setLoadingPdf(true);
                await uploadFile(caseId, file);
            }
            if (type === "pdf") {
                setMessage("PDF uploaded successfully! Click 'Run AI Analysis' below.");
            } else {
                setMessage("Upload successful! Click 'Run AI Analysis' below.");
            }
            onUploadSuccess();
        } catch (e: any) {
            setMessage(`Error: ${e.message}`);
        } finally {
            if (type === "audio") setLoadingAudio(false);
            if (type === "image") setLoadingImage(false);
            if (type === "pdf") setLoadingPdf(false);
            setTimeout(() => setMessage(""), 8000);
        }
    };

    const { getRootProps: getPdfProps, getInputProps: getPdfInput } = useDropzone({
        onDrop: (f) => handleUpload(f, "pdf"),
        accept: { "application/pdf": [".pdf"] },
        multiple: false,
    });

    const { getRootProps: getAudioProps, getInputProps: getAudioInput } = useDropzone({
        onDrop: (f) => handleUpload(f, "audio"),
        accept: { "audio/*": [".mp3", ".wav", ".m4a"] },
        multiple: false,
    });

    const { getRootProps: getImageProps, getInputProps: getImageInput } = useDropzone({
        onDrop: (f) => handleUpload(f, "image"),
        accept: { "image/*": [".png", ".jpg", ".jpeg"] },
        multiple: false,
    });

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div
                    {...getPdfProps()}
                    className="border-2 border-dashed border-slate-300 rounded-lg p-6 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-slate-50 hover:border-blue-400 transition-colors"
                >
                    <input {...getPdfInput()} />
                    {loadingPdf ? (
                        <Loader2 className="h-8 w-8 text-blue-500 animate-spin mb-2" />
                    ) : (
                        <FileUp className="h-8 w-8 text-slate-400 mb-2" />
                    )}
                    <span className="text-sm font-medium text-slate-700">Upload PDF Note</span>
                    <span className="text-xs text-slate-500 mt-1">H&P, Discharge Summary</span>
                </div>

                <div
                    {...getAudioProps()}
                    className="border-2 border-dashed border-slate-300 rounded-lg p-6 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-slate-50 hover:border-blue-400 transition-colors"
                >
                    <input {...getAudioInput()} />
                    {loadingAudio ? (
                        <Loader2 className="h-8 w-8 text-blue-500 animate-spin mb-2" />
                    ) : (
                        <FileAudio className="h-8 w-8 text-slate-400 mb-2" />
                    )}
                    <span className="text-sm font-medium text-slate-700">Upload Dictation</span>
                    <span className="text-xs text-slate-500 mt-1">.mp3, .wav (Whisper)</span>
                </div>

                <div
                    {...getImageProps()}
                    className="border-2 border-dashed border-slate-300 rounded-lg p-6 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-slate-50 hover:border-blue-400 transition-colors"
                >
                    <input {...getImageInput()} />
                    {loadingImage ? (
                        <Loader2 className="h-8 w-8 text-blue-500 animate-spin mb-2" />
                    ) : (
                        <FileImage className="h-8 w-8 text-slate-400 mb-2" />
                    )}
                    <span className="text-sm font-medium text-slate-700">Upload Image</span>
                    <span className="text-xs text-slate-500 mt-1">.png, .jpg (MedGemma Vision)</span>
                </div>
            </div>
            {message && (
                <div className="text-sm text-center py-2 bg-blue-50 text-blue-700 rounded-md font-medium">
                    {message}
                </div>
            )}
        </div>
    );
}
