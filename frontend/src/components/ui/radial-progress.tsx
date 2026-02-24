import * as React from "react"
import { cn } from "@/lib/utils"

interface RadialProgressProps extends React.HTMLAttributes<HTMLDivElement> {
    value: number
    size?: number
    strokeWidth?: number
    indicatorClassName?: string
    trackClassName?: string
}

export function RadialProgress({
    value,
    size = 80,
    strokeWidth = 8,
    indicatorClassName,
    trackClassName,
    className,
    children,
    ...props
}: RadialProgressProps) {
    const radius = (size - strokeWidth) / 2
    const circumference = radius * 2 * Math.PI
    const offset = circumference - (value / 100) * circumference

    return (
        <div
            className={cn("relative inline-flex items-center justify-center", className)}
            style={{ width: size, height: size }}
            {...props}
        >
            <svg className="transform -rotate-90 w-full h-full">
                <circle
                    className={cn("text-slate-100", trackClassName)}
                    strokeWidth={strokeWidth}
                    stroke="currentColor"
                    fill="transparent"
                    r={radius}
                    cx={size / 2}
                    cy={size / 2}
                />
                <circle
                    className={cn("text-blue-600 transition-all duration-1000 ease-in-out", indicatorClassName)}
                    strokeWidth={strokeWidth}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    r={radius}
                    cx={size / 2}
                    cy={size / 2}
                />
            </svg>
            <div className="absolute flex items-center justify-center">
                {children || <span className="text-sm font-semibold">{Math.round(value)}%</span>}
            </div>
        </div>
    )
}
