import type { HTMLAttributes } from "react"

export function Card({className="",...props}:HTMLAttributes<HTMLDivElement>){return <div data-slot="card" className={`rounded-xl border bg-card text-card-foreground ${className}`} {...props}/>}
export function CardHeader({className="",...props}:HTMLAttributes<HTMLDivElement>){return <div data-slot="card-header" className={`flex flex-row items-center justify-between space-y-0 ${className}`} {...props}/>}
export function CardAction({className="",...props}:HTMLAttributes<HTMLDivElement>){return <div data-slot="card-action" className={className} {...props}/>}
export function CardContent({className="",...props}:HTMLAttributes<HTMLDivElement>){return <div data-slot="card-content" className={className} {...props}/>}
