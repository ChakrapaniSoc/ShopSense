import type { ReactNode } from "react"
import { Card, CardAction, CardContent, CardHeader } from "./card"

type Tone="neutral"|"info"|"success"|"warning"|"danger"|"brand"
type Props={label:ReactNode;value:ReactNode;description?:ReactNode;icon?:ReactNode;tone?:Tone;className?:string}

/**
 * ShopSense's local source copy follows Vibra UI's free Stat Card pattern and
 * shadcn's copy-into-your-repository component model. The dashboard owns its
 * navy palette while keeping the same label/value/meta/action composition.
 */
export function StatCard({label,value,description,icon,tone="neutral",className=""}:Props){
  return <Card data-slot="stat-card" data-tone={tone} className={`stat-card ${className}`}>
    <CardHeader>
      <h3 data-slot="stat-card-label">{label}</h3>
      {icon&&<CardAction>{icon}</CardAction>}
    </CardHeader>
    <CardContent>
      <div data-slot="stat-card-value">{value}</div>
      {description&&<p data-slot="stat-card-description">{description}</p>}
    </CardContent>
  </Card>
}
