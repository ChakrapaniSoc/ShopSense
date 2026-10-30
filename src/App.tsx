import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, Check, ChevronDown, CircleHelp, Heart, Leaf, LoaderCircle, Menu, Minus, Plus, Search, ShoppingBag, ShoppingCart, Sparkles, X } from "lucide-react"
import { Bar, BarChart, CartesianGrid, Cell, Funnel, FunnelChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { StatCard } from "@/components/ui/stat-card"

type Product = { id:string; name:string; category:string; description:string; price:number; image_url:string; featured:boolean }
type CartLine = { product:Product; quantity:number }
type Metric = { total_sessions:number; unique_customers:number; purchases:number; conversion_rate:number; cart_abandonment_rate:number; checkout_abandonment_rate:number; average_session_duration:number; average_order_value:number; revenue_by_category:{name:string;value:number}[]; conversion_by_device:{name:string;value:number}[]; popular_actions:{name:string;value:number}[]; common_sequences:{name:string;value:number}[] }
type Dashboard = { source:string; metrics:Metric; funnel:{stage:string;value:number}[]; event_feed:EventRecord[] }
type EventRecord = { id:number; session_id:string; action:string; product_id?:string|null; product_name?:string|null; quantity:number; created_at:string }
type Journey = { session_id:string; customer_id:string; device_type:string; timestamp:string; actions:string[]; dfa:{state_history:string[];final_state:string;status:string;accepted:boolean;transitions:{previous_state:string;action:string;next_state:string;explanation:string}[]} }
type Segments = { error:string|null; customers:Record<string,number|string>[]; summary:Record<string,number|string>[] }
type Patterns = { error:string|null; rules:{antecedents:string;consequents:string;support:number;confidence:number;lift:number}[] }
const API = import.meta.env.VITE_API_BASE_URL || ""
const money = (n:number) => new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:0}).format(n||0)
const fmtNumber = (n:number) => new Intl.NumberFormat("en-IN").format(n||0)
const timestamp = (d:string) => new Date(d).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})
const palette = ["#a78bfa","#22d3ee","#818cf8","#2dd4bf","#f0abfc","#60a5fa"]

async function api<T>(path:string, init?:RequestInit):Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: {"Content-Type":"application/json", ...(init?.headers||{})} })
  if (!response.ok) { let message = `Request failed (${response.status})`; try { message = (await response.json()).detail || message } catch {} throw new Error(message) }
  return response.json()
}
function identity(key:string, storage:Storage=localStorage) {
  let value = storage.getItem(key)
  if (!value) { value = crypto.randomUUID(); storage.setItem(key,value) }
  return value
}
function currentDevice() { return /Mobi|Android/i.test(navigator.userAgent) ? "Mobile" : /iPad|Tablet/i.test(navigator.userAgent) ? "Tablet" : "Desktop" }
function imageFallback(event:React.SyntheticEvent<HTMLImageElement>) {
  event.currentTarget.onerror=null
  event.currentTarget.src=`data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 900"><rect width="800" height="900" fill="#eee9df"/><path d="M0 650 230 410l150 150 115-125 305 280v185H0z" fill="#d8d0c2"/><circle cx="575" cy="245" r="85" fill="#e2dacd"/><text x="400" y="790" text-anchor="middle" fill="#766e62" font-family="sans-serif" font-size="25">Image unavailable</text></svg>')}`
}

export default function App() {
  const [view,setView]=useState<"shop"|"dashboard">("shop")
  const [products,setProducts]=useState<Product[]>([])
  const [loadingProducts,setLoadingProducts]=useState(true)
  const [productError,setProductError]=useState("")
  const [issue,setIssue]=useState("")
  const [cart,setCart]=useState<CartLine[]>(()=>{try{const saved=JSON.parse(localStorage.getItem("shopsense-cart")||"[]");return Array.isArray(saved)?saved.filter((line):line is CartLine=>line?.product?.id&&Number.isInteger(line.quantity)&&line.quantity>0&&line.quantity<=20):[]}catch{return []}})
  const [cartOpen,setCartOpen]=useState(false)
  const [checkoutMessage,setCheckoutMessage]=useState("")
  const [checkoutBusy,setCheckoutBusy]=useState(false)
  const [category,setCategory]=useState("All")
  const [search,setSearch]=useState("")
  const searchRef=useRef<HTMLInputElement>(null)
  const eventQueue=useRef<Promise<void>>(Promise.resolve())

  const [sessionId,setSessionId]=useState(()=>identity("shopsense-session",sessionStorage))
  const customerId=useMemo(()=>identity("shopsense-customer"),[])
  const track=useCallback((action:string,productId?:string,quantity=1):Promise<boolean>=>{
    let saved=false
    eventQueue.current=eventQueue.current.then(async()=>{await api<EventRecord>("/api/events",{method:"POST",body:JSON.stringify({session_id:sessionId,customer_id:customerId,device_type:currentDevice(),action,product_id:productId,quantity})});saved=true;setIssue("")}).catch(error=>{setIssue(error instanceof Error?error.message:"Could not save this shopping event.")})
    return eventQueue.current.then(()=>saved)
  },[sessionId,customerId])

  useEffect(()=>{localStorage.setItem("shopsense-cart",JSON.stringify(cart))},[cart])

  useEffect(()=>{
    let active=true
    api<Product[]>("/api/products").then(items=>{if(active){setProducts(items);setProductError("");setIssue("")}}).catch(error=>{if(active){setProductError(error.message);setIssue(error.message)}}).finally(()=>{if(active)setLoadingProducts(false)})
    const browseKey=`shopsense-browse-recorded:${sessionId}`
    if(!sessionStorage.getItem(browseKey)){void track("Browse");sessionStorage.setItem(browseKey,"yes")}
    return ()=>{active=false}
  },[track,sessionId])
  useEffect(()=>{const onKey=(event:KeyboardEvent)=>{if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==="k"){event.preventDefault();searchRef.current?.focus()}};window.addEventListener("keydown",onKey);return()=>window.removeEventListener("keydown",onKey)},[])

  const categories=useMemo(()=>["All",...new Set(products.map(p=>p.category))],[products])
  const shown=useMemo(()=>products.filter(p=>(category==="All"||p.category===category)&&`${p.name} ${p.category} ${p.description}`.toLowerCase().includes(search.toLowerCase())),[products,category,search])
  const cartCount=cart.reduce((total,line)=>total+line.quantity,0)
  const cartTotal=cart.reduce((total,line)=>total+line.product.price*line.quantity,0)
  function add(product:Product){ setCart(lines=>{const found=lines.find(l=>l.product.id===product.id);if(found&&found.quantity>=20)return lines;return found?lines.map(l=>l.product.id===product.id?{...l,quantity:l.quantity+1}:l):[...lines,{product,quantity:1}]});void track("View Product",product.id);void track("Add to Cart",product.id);setCheckoutMessage("") }
  function remove(productId:string){const line=cart.find(l=>l.product.id===productId);if(line)void track("Remove from Cart",productId);setCart(lines=>lines.filter(l=>l.product.id!==productId))}
  function decrement(productId:string){void track("Remove from Cart",productId);setCart(lines=>lines.flatMap(line=>line.product.id!==productId?line:line.quantity>1?[{...line,quantity:line.quantity-1}]:[]))}
  async function checkout(){
    if(!cart.length||checkoutBusy)return
    setCheckoutBusy(true)
    try { const checkoutEventSaved=await track("Checkout");if(!checkoutEventSaved)throw new Error("The checkout event could not be saved, so the order was not submitted.");const result=await api<{total:number;message:string}>("/api/checkout",{method:"POST",body:JSON.stringify({session_id:sessionId,customer_id:customerId,device_type:currentDevice(),items:cart.map(l=>({product_id:l.product.id,quantity:l.quantity}))})});setCart([]);setCheckoutMessage(`${result.message} Your total was ${money(result.total)}.`);setCartOpen(false);setIssue("");const nextSession=crypto.randomUUID();sessionStorage.setItem("shopsense-session",nextSession);setSessionId(nextSession) }
    catch(error){setIssue(error instanceof Error?error.message:"Checkout could not be completed.")}finally{setCheckoutBusy(false)}
  }

  return <div className={view==="shop"?"store-shell":"dashboard-shell"}>
    <header className={view==="shop"?"store-nav":"dashboard-nav"}>
      <button className="brand-lockup" onClick={()=>setView("shop")} aria-label="ShopSense storefront"><span className="brand-mark"><Leaf size={17}/></span><span>shopsense<span className="brand-period">.</span></span></button>
      {view==="shop"?<>
        <nav className="store-links"><a href="#new">New arrivals</a><a href="#collection">Collection</a><a href="#story">Our point of view</a></nav>
        <div className="nav-actions"><button className="dashboard-link" onClick={()=>setView("dashboard")}><BarChart3 size={16}/> Live insights</button><button className="cart-button" onClick={()=>setCartOpen(true)} aria-label={`Open cart, ${cartCount} items`}><ShoppingBag size={19}/><span>Bag</span><i>{cartCount}</i></button><button className="mobile-menu" aria-label="Open menu"><Menu/></button></div>
      </>:<>
        <div className="dashboard-location"><span className="crumb-dim">Studio</span><span className="crumb-slash">/</span><span>Live analytics</span></div>
        <button className="back-to-store" onClick={()=>setView("shop")}><ShoppingBag size={15}/> View storefront</button>
      </>}
    </header>
    {issue&&<div className={view==="shop"?"connection-banner":"dashboard-connection"}><CircleHelp size={16}/><span>{issue}</span><button onClick={()=>{setIssue("");if(view==="dashboard")window.location.reload()}}>Dismiss</button></div>}
    {view==="shop"?<main className="store-main">
      <section className="store-hero" id="story"><div className="hero-copy"><div className="eyebrow"><span/> CONSIDERED GOODS · EST. 2025</div><h1>Make room for<br/><em>the everyday.</em></h1><p>Well-made things for living well. A small collection of objects chosen for how they feel, how they last, and the quiet joy they bring.</p><a href="#collection" className="hero-cta">Explore the collection <ArrowRight size={16}/></a><div className="hero-footnote"><span>01 — 08</span><div className="hero-line"/><span>Objects with intention</span></div></div>
        <div className="hero-image"><img src="https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=1500&q=90" alt="Sunlit, thoughtfully arranged home objects"/><div className="image-note"><span>THE SLOW LIVING EDIT</span><ArrowUpRight size={15}/></div><div className="image-number">A quieter kind<br/>of beautiful.</div></div>
      </section>
      <section className="values-strip"><div><span>01</span> Made to be lived with</div><div><span>02</span> Materials with a story</div><div><span>03</span> Thoughtful by design</div><div className="values-note"><Sparkles size={15}/> A little less, a little better</div></section>
      {checkoutMessage&&<div className="success-banner"><Check size={17}/>{checkoutMessage}<button onClick={()=>setCheckoutMessage("")}><X size={16}/></button></div>}
      <section className="collection" id="collection">
        <div className="section-heading"><div><div className="eyebrow">THE SHOP · 2025 COLLECTION</div><h2>Things worth keeping.</h2><p>Every piece has a place in the way we live.</p></div><button className="text-link" onClick={()=>setView("dashboard")}>The story behind the shop <ArrowRight size={15}/></button></div>
        <div className="catalog-tools"><div className="category-pills">{categories.map(item=><button key={item} className={category===item?"category-pill active":"category-pill"} onClick={()=>setCategory(item)}>{item}</button>)}</div><label className="search-box"><Search size={16}/><input ref={searchRef} value={search} onChange={e=>setSearch(e.target.value)} placeholder="Find something lovely"/><kbd>⌘ K</kbd></label></div>
        {loadingProducts?<div className="loading-state"><LoaderCircle className="spin"/> Gathering the collection…</div>:productError?<div className="empty-products"><p>We couldn’t load the collection: {productError}</p><button className="add-button" onClick={()=>window.location.reload()}>Retry loading products</button></div>:shown.length?<div className="product-grid">{shown.map((product,index)=><article className="product-card" key={product.id}>
          <div className="product-image" role="button" tabIndex={0} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();void track("View Product",product.id)}}} onClick={()=>void track("View Product",product.id)} aria-label={`View ${product.name}`}><img src={product.image_url} onError={imageFallback} alt={product.name} loading={index>3?"lazy":"eager"}/>{product.featured&&<span className="product-tag">A SHOP FAVOURITE</span>}<span className="quick-view">Take a closer look <ArrowUpRight size={14}/></span><button className="save-button" onClick={e=>{e.stopPropagation();void track("View Product",product.id)}} aria-label="Save item"><Heart size={17}/></button></div>
          <div className="product-meta"><div><span className="product-category">{product.category}</span><h3>{product.name}</h3></div><span className="product-price">{money(product.price)}</span></div><div className="product-bottom"><p>{product.description}</p><button className="add-button" onClick={()=>add(product)}><Plus size={15}/> Add to bag</button></div>
        </article>)}</div>:<div className="empty-products">Nothing in this corner just yet. Try another search.</div>}
        <div className="collection-end"><span>Showing {shown.length} considered pieces</span><span>COMMERCE WITHOUT THE NOISE</span></div>
      </section>
      <section className="closing-note"><div className="closing-star">✳</div><p>“Buy less. Choose well.<br/><em>Make it last.</em>”</p><span>A NOTE ON HOW WE SHOP</span></section>
      <footer className="store-footer"><span>© 2025 ShopSense Studio</span><span>Thoughtfully put together, for demonstration.</span><button onClick={()=>setView("dashboard")}>Shop intelligence <ArrowRight size={14}/></button></footer>
    </main>:<DashboardPage/>}

    {cartOpen&&<><button className="scrim" aria-label="Close bag" onClick={()=>setCartOpen(false)}/><aside className="cart-drawer"><div className="drawer-heading"><div><span className="eyebrow">YOUR EDIT</span><h2>The bag <span>({cartCount})</span></h2></div><button className="icon-button" onClick={()=>setCartOpen(false)} aria-label="Close bag"><X/></button></div>
      {cart.length?<><div className="cart-lines">{cart.map(line=><div className="cart-line" key={line.product.id}><img src={line.product.image_url} onError={imageFallback} alt={line.product.name}/><div className="cart-line-info"><span>{line.product.category}</span><h3>{line.product.name}</h3><b>{money(line.product.price)}{line.quantity>1?` · Qty ${line.quantity}`:""}</b><button onClick={()=>remove(line.product.id)}>Remove</button></div><div className="qty-control"><button disabled={line.quantity<=1} onClick={()=>decrement(line.product.id)} aria-label="Decrease quantity"><Minus size={12}/></button><span>{line.quantity}</span><button disabled={line.quantity>=20} onClick={()=>{setCart(items=>items.map(i=>i.product.id===line.product.id&&i.quantity<20?{...i,quantity:i.quantity+1}:i));void track("Add to Cart",line.product.id)}} aria-label="Increase quantity"><Plus size={12}/></button></div></div>)}</div><div className="cart-summary"><div><span>Subtotal</span><b>{money(cartTotal)}</b></div><p>Shipping and taxes are worked out at checkout.</p><button className="checkout-button" disabled={checkoutBusy} onClick={checkout}>{checkoutBusy?"Confirming demo order…":"Complete demo checkout"} {!checkoutBusy&&<ArrowRight size={16}/>}</button><button className="clear-cart-button" onClick={()=>{cart.forEach(line=>void track("Remove from Cart",line.product.id,line.quantity));setCart([])}}>Clear bag</button><small>No payment details are collected.</small></div></>:<div className="cart-empty"><span className="bag-icon"><ShoppingBag size={25}/></span><h3>Your bag is taking a breath.</h3><p>When something catches your eye, it’ll be here.</p><button onClick={()=>setCartOpen(false)}>Back to the collection <ArrowRight size={15}/></button></div>}
    </aside></>}
  </div>
}

function DashboardPage(){
  const [tab,setTab]=useState("Overview")
  const [dashboard,setDashboard]=useState<Dashboard|null>(null)
  const [journeys,setJourneys]=useState<Journey[]>([])
  const [segments,setSegments]=useState<Segments|null>(null)
  const [patterns,setPatterns]=useState<Patterns|null>(null)
  const [selected,setSelected]=useState("")
  const [loading,setLoading]=useState(true)
  const [connected,setConnected]=useState(false)
  const [status,setStatus]=useState("")
  const selectedJourney=journeys.find(j=>j.session_id===selected)||journeys[0]
  const refresh=useCallback(async()=>{
    try{const [stats,paths]=await Promise.all([api<Dashboard>("/api/dashboard"),api<Journey[]>("/api/journeys?limit=20")]);setDashboard(stats);setJourneys(paths);setStatus("");setConnected(true);if(!selected&&paths[0])setSelected(paths[0].session_id)}catch(e){setStatus(e instanceof Error?e.message:"Unable to load live analytics.");setConnected(false)}finally{setLoading(false)}
  },[selected])
  useEffect(()=>{void refresh();const timer=window.setInterval(()=>void refresh(),5000);return()=>window.clearInterval(timer)},[refresh])
  useEffect(()=>{if(tab==="Segments")api<Segments>("/api/segments").then(setSegments).catch(e=>setSegments({error:e.message,customers:[],summary:[]}));if(tab==="Product patterns")api<Patterns>("/api/patterns").then(setPatterns).catch(e=>setPatterns({error:e.message,rules:[]}))},[tab])
  const m=dashboard?.metrics
  const nav=[{name:"Overview",icon:BarChart3},{name:"Customer journeys",icon:Activity},{name:"Segments",icon:CircleHelp},{name:"Product patterns",icon:Sparkles}]
  return <div className="analytics-layout">
    <aside className="analytics-sidebar"><div className="workspace-label">WORKSPACE</div><div className="workspace-card"><div className="workspace-avatar">S</div><div><b>ShopSense Studio</b><small>Live commerce demo</small></div><ChevronDown size={14}/></div><div className="sidebar-section-label">ANALYZE</div><nav className="analytics-menu">{nav.map(item=><button key={item.name} onClick={()=>setTab(item.name)} className={tab===item.name?"analytics-nav active":"analytics-nav"}><item.icon size={17}/>{item.name}{item.name==="Customer journeys"&&journeys.length>0&&<span>{journeys.length}</span>}</button>)}</nav><div className="sidebar-bottom"><div className="db-health"><i style={{background:connected?"#2dd4a3":"#ed8b9b"}}/><div><b>{connected?"PostgreSQL connected":"Database unavailable"}</b><small>Persisted events · refreshes every 5s</small></div></div><button className="sidebar-help"><CircleHelp size={16}/> How this works</button><div className="sidebar-profile"><div className="profile-avatar">SS</div><div><b>Studio Admin</b><small>Analytics workspace</small></div><ChevronDown size={14}/></div></div></aside>
    <main className="analytics-main"><div className="analytics-topline"><div className="analytics-breadcrumb">Analytics <span>/</span> <b>{tab}</b></div><div className="topline-actions"><span className="live-pill" style={!connected?{color:"#f1a9b5",borderColor:"#633d49"}:{}}><i style={!connected?{background:"#ed8b9b",boxShadow:"none"}:{}}/> {connected?"LIVE":"OFFLINE"}</span><span className="updated-label">Polling every 5 seconds</span><span className="date-select">All time</span><button className="avatar-mini">S</button></div></div>
    {loading&&!dashboard&&<div className="analytics-loading"><LoaderCircle className="spin"/>Connecting to the live event stream…</div>}
      {status&&!dashboard&&<div className="analytics-error"><CircleHelp size={16}/><div><b>Live data unavailable</b><p>{status}</p></div></div>}
      {!dashboard&&!loading&&<section className="panel empty-panel"><Activity/><h3>Live metrics are withheld until the database connects</h3><p>Set DATABASE_URL and apply migrations/001_initial.sql. The storefront will then load real products and write events to PostgreSQL.</p></section>}
      {dashboard&&<>
      {tab==="Overview"&&<>
        <div className="analytics-title-row"><div><div className="analytics-kicker">COMMERCE INTELLIGENCE <span>·</span> LIVE DATA</div><h1>Live commerce overview.</h1><p>Your storefront is telling a story. Here’s what’s happening right now.</p></div><div className="title-actions"><span className="actual-data"><span/> Actual persisted events</span><button className="export-button" onClick={()=>void refresh()}><Activity size={15}/> Refresh now</button></div></div>
        <div className="metrics-grid">{[
          {label:"Total sessions",value:fmtNumber(m?.total_sessions||0),description:"Persisted shopping journeys",icon:<Activity size={17}/>,tone:"info" as const},
          {label:"Purchase conversion",value:`${(m?.conversion_rate||0).toFixed(1)}%`,description:`${fmtNumber(m?.purchases||0)} simulated purchases`,icon:<ArrowUpRight size={17}/>,tone:"success" as const},
          {label:"Gross revenue",value:money((m?.revenue_by_category||[]).reduce((a,b)=>a+b.value,0)),description:"From completed demo checkouts",icon:<ShoppingCart size={17}/>,tone:"brand" as const},
          {label:"Average order value",value:money(m?.average_order_value||0),description:`${fmtNumber(m?.unique_customers||0)} anonymous shoppers`,icon:<Sparkles size={17}/>,tone:"warning" as const},
        ].map(card=><StatCard key={card.label} className="live-stat-card" label={card.label} value={card.value} description={card.description} icon={card.icon} tone={card.tone}/> )}</div>
        <div className="chart-grid"><section className="panel funnel-panel"><div className="panel-heading"><div><h2>Shopping funnel</h2><p>How live sessions move through the store</p></div><span className="panel-chip">ALL SESSIONS</span></div><div className="chart-wrap funnel-wrap">{dashboard?.funnel.some(d=>d.value>0)?<ResponsiveContainer width="100%" height="100%"><FunnelChart><Tooltip contentStyle={{background:"#131c31",border:"1px solid #293650",borderRadius:12,color:"#eef2ff"}}/><Funnel dataKey="value" data={dashboard.funnel} isAnimationActive fill="#8b7bff" stroke="#151d31">{dashboard.funnel.map((_,i)=><Cell key={i} fill={palette[i%palette.length]}/>)}</Funnel></FunnelChart></ResponsiveContainer>:<EmptyChart text="Shop activity will shape your funnel."/>}</div><div className="funnel-labels">{dashboard?.funnel.map((step,i)=><div key={step.stage}><i style={{background:palette[i%palette.length]}}/><span>{step.stage}</span><b>{step.value}</b></div>)}</div></section>
          <section className="panel category-panel"><div className="panel-heading"><div><h2>Revenue by category</h2><p>Confirmed demo orders, by collection</p></div><span className="panel-chip">LIVE POSTGRES</span></div><div className="chart-wrap">{m?.revenue_by_category.length?<ResponsiveContainer width="100%" height="100%"><BarChart data={m.revenue_by_category} margin={{top:10,right:5,left:2,bottom:0}}><CartesianGrid stroke="#222d42" vertical={false}/><XAxis dataKey="name" tick={{fill:"#8894ae",fontSize:11}} axisLine={false} tickLine={false}/><YAxis tick={{fill:"#8894ae",fontSize:11}} axisLine={false} tickLine={false} tickFormatter={v=>`₹${v/1000}k`}/><Tooltip formatter={(v)=>money(Number(v))} contentStyle={{background:"#131c31",border:"1px solid #293650",borderRadius:12,color:"#eef2ff"}}/><Bar dataKey="value" name="Revenue" radius={[7,7,0,0]}>{m.revenue_by_category.map((_,i)=><Cell key={i} fill={palette[i%palette.length]}/>)}</Bar></BarChart></ResponsiveContainer>:<EmptyChart text="Revenue appears after a demo checkout."/>}</div><div className="chart-legend">{(m?.revenue_by_category||[]).slice(0,4).map((r,i)=><span key={r.name}><i style={{background:palette[i]}}/>{r.name} <b>{money(r.value)}</b></span>)}</div></section></div>
        <div className="lower-grid"><section className="panel activity-panel"><div className="panel-heading"><div><h2>Live activity</h2><p>Latest events written to the database</p></div><span className="live-indicator"><i/> POLLING</span></div>{dashboard?.event_feed.length?<div className="event-list">{dashboard.event_feed.slice(0,9).map(event=><div className="event-row" key={event.id}><span className={`event-icon event-${event.action.toLowerCase().replaceAll(" ","-")}`}><EventIcon action={event.action}/></span><div className="event-copy"><b>{event.action}</b><span>{event.product_name||"Storefront"}<i>·</i><code>{event.session_id.slice(0,12)}</code></span></div><time>{timestamp(event.created_at)}</time></div>)}</div>:<EmptyChart text="Browse the storefront to create the first event."/>}</section>
          <section className="panel device-panel"><div className="panel-heading"><div><h2>Device conversion</h2><p>Purchases / sessions by device</p></div><span className="panel-chip">LIVE</span></div>{m?.conversion_by_device.length?<div className="device-list">{m.conversion_by_device.map((device,i)=><div className="device-row" key={device.name}><span className="device-dot" style={{background:palette[i]}}/><span>{device.name}</span><div className="device-track"><i style={{width:`${Math.max(3,device.value)}%`,background:palette[i]}}/></div><b>{device.value.toFixed(1)}%</b></div>)}</div>:<EmptyChart text="Device detail appears with shopping activity."/>}<div className="device-note"><ArrowDownRight size={14}/> Events are grouped by anonymous browser session.</div></section></div>
        <JourneyPanel journeys={journeys} selected={selectedJourney} onSelect={setSelected}/>
        <div className="analytics-footer"><span>ShopSense intelligence · powered by persisted PostgreSQL events</span><span>DEMO CHECKOUT · NO PAYMENT INFORMATION</span></div>
      </>}
      {tab==="Customer journeys"&&<><div className="analytics-title-row"><div><div className="analytics-kicker">SESSION TRACE</div><h1>Customer journeys</h1><p>Ordered events are read from Postgres and replayed through the live DFA.</p></div><span className="actual-data"><span/> {journeys.length} recent sessions</span></div><JourneyPanel journeys={journeys} selected={selectedJourney} onSelect={setSelected} expanded/></>}
      {tab==="Segments"&&<><div className="analytics-title-row"><div><div className="analytics-kicker">BEHAVIOUR GROUPS</div><h1>Customer segments</h1><p>Scaled KMeans clusters calculated from real persisted demo sessions.</p></div></div>{segments?.error?<div className="panel empty-panel"><Sparkles/><h3>Segments will appear after a few sessions</h3><p>{segments.error}</p></div>:segments?<><div className="segment-summary-grid">{segments.summary.map(row=><div className="segment-card" key={String(row.cluster)}><span>CLUSTER {row.cluster}</span><b>{fmtNumber(Number(segments.customers.filter(c=>c.cluster===row.cluster).length))}</b><small>anonymous shoppers</small><div>Sessions per customer <strong>{Number(row.number_of_sessions).toFixed(1)}</strong></div><div>Purchase frequency <strong>{(Number(row.purchase_conversion_frequency)*100).toFixed(1)}%</strong></div><div>Cart abandonment <strong>{fmtNumber(Number(row.cart_abandonment_frequency))}</strong></div></div>)}</div><section className="panel table-panel"><div className="panel-heading"><div><h2>Customer-level features</h2><p>IDs are anonymous and excluded from model inputs.</p></div></div><DataTable rows={segments.customers.slice(0,30)} columns={["customer_id","number_of_sessions","total_purchases","average_session_duration","average_order_value","purchase_conversion_frequency","cluster"]}/></section></>:<div className="analytics-loading"><LoaderCircle className="spin"/>Calculating customer segments…</div>}</>}
      {tab==="Product patterns"&&<><div className="analytics-title-row"><div><div className="analytics-kicker">CO-OCCURRENCE · NOT CAUSATION</div><h1>Product patterns</h1><p>Apriori association rules from completed, persisted demo orders.</p></div><span className="actual-data"><span/> Live purchase baskets</span></div>{patterns?.error?<div className="panel empty-panel"><Sparkles/><h3>Patterns are waiting for a few purchases</h3><p>{patterns.error}</p></div>:patterns?<><div className="pattern-explain"><div><b>Support</b><span>How often both items appear in all baskets.</span></div><div><b>Confidence</b><span>How often the right side appears with the left.</span></div><div><b>Lift</b><span>Strength versus the right side’s baseline frequency.</span></div><small>Co-occurrence does not establish causation.</small></div><section className="panel table-panel"><div className="panel-heading"><div><h2>Frequent product associations</h2><p>{patterns.rules.length} rules meet the current thresholds</p></div></div>{patterns.rules.length?<DataTable rows={patterns.rules} columns={["antecedents","consequents","support","confidence","lift"]}/>:<EmptyChart text="No purchase combinations meet the current support threshold."/>}</section></>:<div className="analytics-loading"><LoaderCircle className="spin"/>Mining persisted purchase baskets…</div>}</>}
      </>}
    </main>
  </div>
}

function EventIcon({action}:{action:string}){if(action.includes("Cart"))return <ShoppingCart size={15}/>;if(action==="Purchase")return <Check size={15}/>;if(action==="Checkout")return <ArrowRight size={15}/>;if(action==="View Product")return <Search size={15}/>;return <Activity size={15}/>}
function EmptyChart({text}:{text:string}){return <div className="empty-chart"><span><Activity size={18}/></span><p>{text}</p></div>}
function DataTable({rows,columns}:{rows:Record<string,any>[];columns:string[]}){return <div className="data-table-scroll"><table className="data-table"><thead><tr>{columns.map(c=><th key={c}>{c.replaceAll("_"," ")}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={String(row.id||row.customer_id||i)}>{columns.map(col=><td key={col}>{typeof row[col]==="number"?Number(row[col]).toFixed(2):String(row[col]??"—")}</td>)}</tr>)}</tbody></table></div>}
function JourneyPanel({journeys,selected,onSelect,expanded=false}:{journeys:Journey[];selected?:Journey;onSelect:(id:string)=>void;expanded?:boolean}){
  const states=selected?.dfa.state_history||["S0"]
  return <section className={`panel journey-panel ${expanded?"journey-expanded":""}`}><div className="panel-heading"><div><h2>Deterministic automaton</h2><p>Actual ordered events processed through the ShopSense DFA</p></div><span className={`journey-status status-${selected?.dfa.status||"incomplete"}`}>{selected?.dfa.status||"awaiting events"}</span></div>
    {journeys.length?<div className="journey-content"><div className="journey-list">{journeys.slice(0,10).map(j=><button key={j.session_id} className={j.session_id===selected?.session_id?"journey-select selected":"journey-select"} onClick={()=>onSelect(j.session_id)}><span><b>{j.session_id.slice(0,15)}</b><small>{j.device_type} · {j.actions.length} events</small></span><ArrowRight size={14}/></button>)}</div><div className="journey-detail"><div className="journey-session-meta"><span>SELECTED SESSION</span><code>{selected?.session_id||"No session"}</code></div><div className="dfa-flow">{states.map((state,i)=><div className="dfa-node-wrap" key={`${state}-${i}`}><div className={`dfa-node ${state===selected?.dfa.final_state?`dfa-${selected?.dfa.status}`:""} ${state==="S4"?"dfa-accepting":""}`}><b>{state}</b><small>{stateLabel(state)}</small></div>{i<states.length-1&&<div className="dfa-edge"><ArrowRight size={14}/><small>{selected?.actions[i]}</small></div>}</div>)}</div><div className="journey-explanation"><span className="journey-dot"/><p>{selected?.dfa.transitions.at(-1)?.explanation||"A session is created as shoppers interact with the store. Its state history will appear here."}</p></div></div></div>:<EmptyChart text="No persisted sessions yet. Open the storefront and browse a product."/>}
  </section>
}
function stateLabel(state:string){return ({S0:"Started",S1:"Viewed",S2:"In cart",S3:"Checkout",S4:"Purchased",S5:"Abandoned",SD:"Invalid"} as Record<string,string>)[state]||state}
