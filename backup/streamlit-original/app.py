"""ShopSense: an automata-based shopping behaviour teaching dashboard."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from data.generate_data import generate_sessions
from modules.analytics import REQUIRED_COLUMNS, calculate_metrics, segment_customers, validate_data
from modules.automata import ALPHABET, ACCEPTING_STATES, STATE_NAMES, TRANSITIONS, process_actions
from modules.pattern_mining import mine_patterns

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "shopping_data.csv"
st.set_page_config(page_title="ShopSense", page_icon="🛍️", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif} .stApp{background:#0b1020;color:#edf0fb}
[data-testid="stMetric"]{background:linear-gradient(135deg,#171d34,#14192c);padding:18px;border:1px solid #292f4b;border-radius:16px}
.hero{padding:24px 28px;border-radius:20px;background:linear-gradient(115deg,#231b47,#172b50);border:1px solid #34345f;margin-bottom:18px}
.muted{color:#a8afc6} section[data-testid="stSidebar"]{background:#10162a}
</style>""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_default():
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(exist_ok=True); generate_sessions().to_csv(DATA_PATH,index=False)
    return validate_data(pd.read_csv(DATA_PATH))

st.sidebar.title("🛍️ ShopSense")
st.sidebar.caption("Automata-based shopping behaviour analyzer")
page = st.sidebar.radio("Navigation",["Overview","Shopping Behaviour","Automata Simulator","Customer Segments","Product Patterns","Data Explorer","About the Project"])
if st.sidebar.button("Regenerate synthetic dataset", use_container_width=True):
    generate_sessions().to_csv(DATA_PATH,index=False); load_default.clear(); st.session_state.pop("uploaded_data",None); st.rerun()
st.sidebar.caption("All included data is synthetic.")
data = st.session_state.get("uploaded_data")
if data is None:
    try: data = load_default()
    except Exception as exc: st.error(f"Could not load the bundled dataset: {exc}"); st.stop()

def empty_note(): st.info("No sessions match these filters. Adjust the filters to see results.")
def chart_or_note(frame, fn):
    if frame.empty: empty_note()
    else: st.plotly_chart(fn(frame),use_container_width=True)
def metric_cards(metrics):
    cols=st.columns(4)
    specs=[("Sessions",f"{metrics['total_sessions']:,}"),("Customers",f"{metrics['unique_customers']:,}"),("Conversion",f"{metrics['conversion_rate']:.1f}%"),("Revenue",f"₹{data.loc[data.purchase_completed,'total_purchase_amount'].sum():,.0f}")]
    for c,(label,val) in zip(cols,specs): c.metric(label,val)
def state_diagram():
    coords={"S0":(0,0),"S1":(1,0),"S2":(2,0),"S3":(3,0),"S4":(4,0),"S5":(2,-1),"SD":(4,-1)}
    edges=[]
    for (a,act),b in TRANSITIONS.items(): edges.append((a,b,act))
    fig=go.Figure()
    for a,b,label in edges:
        x1,y1=coords[a];x2,y2=coords[b]
        if a==b: continue
        fig.add_annotation(x=x2,y=y2,ax=x1,ay=y1,xref="x",yref="y",axref="x",ayref="y",showarrow=True,arrowhead=2,arrowcolor="#7666ed",text="")
    labels={"S0":"S0 · Start","S1":"S1 · Viewed","S2":"S2 · Cart","S3":"S3 · Checkout","S4":"S4 · Purchase ✓","S5":"S5 · Abandoned","SD":"SD · Invalid"}
    for s,(x,y) in coords.items():
        fig.add_trace(go.Scatter(x=[x],y=[y],mode="markers+text",text=[labels[s]],textposition="bottom center",marker={"size":34,"color":"#41c9a7" if s in ACCEPTING_STATES else "#6557d9" if s not in ["SD","S5"] else "#d77965"},showlegend=False,hovertemplate=f"{s}: {STATE_NAMES[s]}<extra></extra>"))
    fig.update_layout(height=290,margin=dict(l=10,r=10,t=10,b=60),xaxis=dict(visible=False),yaxis=dict(visible=False),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
    return fig

if page == "Overview":
    st.markdown("<div class='hero'><h1>Understand every shopping journey.</h1><p class='muted'>Explore customer actions, discover patterns and see how a deterministic automaton models a session.</p><b>DEMO DATA · Synthetic sessions only · Not actual customer behaviour</b></div>",unsafe_allow_html=True)
    m=calculate_metrics(data); metric_cards(m)
    a,b=st.columns(2)
    with a:
        st.subheader("Session outcomes")
        outcomes=pd.Series({"Purchased":int(data.purchase_completed.sum()),"Checkout abandoned":int((data.checkout_started & ~data.purchase_completed).sum()),"Cart abandoned":int((data.items_added_to_cart.gt(0)&~data.purchase_completed&~data.checkout_started).sum()),"Browsed only":int((data.items_added_to_cart.eq(0)&~data.purchase_completed).sum())})
        st.plotly_chart(px.pie(values=outcomes.values,names=outcomes.index,hole=.55,color_discrete_sequence=["#50d2aa","#8571f2","#3998dc","#555f7c"]),use_container_width=True)
    with b:
        st.subheader("Shopping activity")
        acts=m["popular_actions"]
        chart_or_note(acts.rename_axis("Action").reset_index(name="Count"),lambda x:px.bar(x,x="Action",y="Count",color="Action",color_discrete_sequence=px.colors.qualitative.Pastel))
    c,d=st.columns(2)
    with c: st.subheader("Revenue by category"); chart_or_note(m["revenue_by_category"].rename_axis("Category").reset_index(name="Revenue"),lambda x:px.bar(x,x="Category",y="Revenue",color="Category"))
    with d: st.subheader("Device conversion"); chart_or_note(m["conversion_by_device"].rename_axis("Device").reset_index(name="Conversion %"),lambda x:px.bar(x,x="Device",y="Conversion %",color="Device"))
    st.caption(f"Cart abandonment: {m['cart_abandonment_rate']:.1f}% · Checkout abandonment: {m['checkout_abandonment_rate']:.1f}% · Average order value: ₹{m['average_order_value']:,.2f}")
elif page == "Shopping Behaviour":
    st.title("Shopping Behaviour"); st.caption("Patterns here describe only the selected synthetic or user-uploaded dataset.")
    f1,f2,f3=st.columns(3)
    devices=["All"]+sorted(data.device_type.dropna().astype(str).unique()); cats=["All"]+sorted(data.product_category.dropna().astype(str).unique())
    dv=f1.selectbox("Device",devices);cat=f2.selectbox("Category",cats)
    dates=pd.to_datetime(data.timestamp,errors="coerce").dropna()
    date_range=f3.date_input("Date range",(dates.min().date(),dates.max().date()) if len(dates) else ())
    filtered=data.copy()
    if dv!="All": filtered=filtered[filtered.device_type.astype(str)==dv]
    if cat!="All": filtered=filtered[filtered.product_category.astype(str)==cat]
    if len(date_range)==2: filtered=filtered[pd.to_datetime(filtered.timestamp).dt.date.between(date_range[0],date_range[1])]
    if filtered.empty: empty_note()
    else:
        x,y=st.columns(2)
        with x: st.subheader("Most common action sequences"); seq=filtered.actions.apply(lambda a:" → ".join(a) or "No actions").value_counts().head(10);st.dataframe(seq.rename_axis("Sequence").reset_index(name="Sessions"),use_container_width=True,hide_index=True)
        with y: st.subheader("Outcomes");out=filtered.assign(outcome="Browsed only");out.loc[filtered.items_added_to_cart.gt(0),"outcome"]="Cart journey";out.loc[filtered.checkout_started,"outcome"]="Checkout abandoned";out.loc[filtered.purchase_completed,"outcome"]="Purchased";st.plotly_chart(px.histogram(out,x="product_category",color="outcome",barmode="group"),use_container_width=True)
        st.subheader("Cart analysis");st.write(f"{int((filtered.items_added_to_cart.gt(0)&~filtered.purchase_completed).sum())} sessions added products and did not purchase.")
        st.subheader("Category performance");st.dataframe(filtered.groupby("product_category").agg(sessions=("session_id","count"),purchases=("purchase_completed","sum"),revenue=("total_purchase_amount","sum")).reset_index(),use_container_width=True,hide_index=True)
elif page == "Automata Simulator":
    st.title("Automata Simulator");st.write("The DFA reads one action at a time. It remembers workflow progress in its current state; unavailable transitions enter SD (invalid). Stopping before a purchase can still be a valid incomplete session.")
    example=st.selectbox("Load an example",["Choose…","Successful purchase","Abandoned cart","Browse only","Remove then purchase","Invalid: purchase before checkout"])
    examples={"Successful purchase":["Browse","View Product","Add to Cart","Checkout","Purchase"],"Abandoned cart":["View Product","Add to Cart","Abandon"],"Browse only":["Browse","View Product","View Product"],"Remove then purchase":["View Product","Add to Cart","Remove from Cart","Add to Cart","Checkout","Purchase"],"Invalid: purchase before checkout":["View Product","Add to Cart","Purchase"]}
    if example in examples: st.session_state.sim_actions=examples[example]
    current=st.session_state.get("sim_actions",[])
    action=st.selectbox("Add an action",ALPHABET,key="sim_action")
    col1,col2=st.columns(2)
    if col1.button("Add action"): st.session_state.sim_actions=current+[action];st.rerun()
    if col2.button("Clear sequence"): st.session_state.sim_actions=[];st.rerun()
    st.write("Sequence: "+(" → ".join(current) if current else "(empty — session has just started)"))
    result=process_actions(current)
    color={"completed":"🟢","abandoned":"🟠","incomplete":"🔵","invalid":"🔴"}[result.status]
    st.subheader(f"{color} {result.status.title()} · current state {result.final_state} ({STATE_NAMES[result.final_state]})")
    st.write("State history: "+" → ".join(result.state_history));st.write("Accepting state(s): "+", ".join(sorted(ACCEPTING_STATES)))
    st.dataframe(pd.DataFrame(result.transitions,columns=["previous_state","action","next_state","explanation"]),use_container_width=True,hide_index=True)
    st.plotly_chart(state_diagram(),use_container_width=True)
    with st.expander("DFA concepts"): st.markdown("**Alphabet:** the allowed action symbols. **State:** the automaton's summary of progress. **Transition function:** a deterministic rule mapping current state and action to next state. **Accepting state:** S4, reached only after checkout then purchase. SD records an invalid action order. S0–S3 can be valid incomplete sessions; S5 is a valid abandonment.")
elif page == "Customer Segments":
    st.title("Customer Segments"); st.caption("KMeans uses scaled customer-level behaviour features. Customer IDs are labels, never model inputs.")
    k=st.slider("Number of clusters",2,8,4)
    customers,summary,error=segment_customers(data,k)
    if error: st.info(error)
    else:
        customers=customers.reset_index();summary=summary.reset_index();sizes=customers.cluster.value_counts().sort_index().rename_axis("Cluster").reset_index(name="Customers")
        st.plotly_chart(px.bar(sizes,x="Cluster",y="Customers",color="Cluster"),use_container_width=True)
        st.subheader("Cluster characteristics");st.dataframe(summary.round(2),use_container_width=True,hide_index=True)
        st.subheader("Customer groups");st.plotly_chart(px.scatter(customers,x="number_of_sessions",y="purchase_conversion_frequency",color="cluster",size="total_purchases",hover_data=["customer_id"]),use_container_width=True)
        st.caption("Cluster numbers are arbitrary. Compare their averages before assigning business meaning.")
elif page == "Product Patterns":
    st.title("Product Patterns");st.warning("The bundled product field is category-level synthetic data. Rules are simulated co-occurrences and do not imply causation.")
    c1,c2=st.columns(2);support=c1.slider("Minimum support",.02,.8,.08,.01);confidence=c2.slider("Minimum confidence",.05,1.0,.3,.05)
    rules,error=mine_patterns(data,support,confidence)
    if error: st.info(error)
    else: st.dataframe(rules[["antecedents","consequents","support","confidence","lift"]].head(30).style.format({"support":"{:.1%}","confidence":"{:.1%}","lift":"{:.2f}"}),use_container_width=True,hide_index=True)
    with st.expander("How to read a rule"):
        st.markdown("**Support** is the share of transactions containing both sides. **Confidence** is the share of transactions with the left side that also contain the right side. **Lift** compares that confidence with the right side's overall frequency; above 1 means co-occurrence is more common than that baseline. Association does not establish cause.")
elif page == "Data Explorer":
    st.title("Data Explorer");st.caption("CSV uploads must include every required session column; actions should be JSON lists.")
    upload=st.file_uploader("Upload compatible CSV",type="csv")
    if upload:
        try: st.session_state.uploaded_data=validate_data(pd.read_csv(upload));data=st.session_state.uploaded_data;st.success(f"Loaded {len(data):,} sessions.")
        except Exception as exc: st.error(f"Upload could not be used: {exc}")
    st.write(f"**{len(data):,} rows × {len(data.columns)} columns**")
    st.dataframe(data.head(100),use_container_width=True,hide_index=True)
    st.subheader("Column information");st.dataframe(pd.DataFrame({"column":data.columns,"dtype":data.dtypes.astype(str).values,"missing":data.isna().sum().values}),use_container_width=True,hide_index=True)
    st.download_button("Download current dataset as CSV",data.to_csv(index=False).encode("utf-8"),"shopsense_sessions.csv","text/csv")
elif page == "About the Project":
    st.title("About ShopSense");st.markdown("""
### Problem statement
Shopping event streams can be hard to explain. ShopSense is a classroom demonstration combining a formal workflow model with simple exploratory data science.

### Objectives and concepts
- **DFA:** finite states represent progress; an alphabet contains actions; a transition function deterministically changes state; accepting states identify completed purchase journeys.
- **Data Science:** descriptive metrics, scaled KMeans clustering, and Apriori association rules.
- **Architecture:** Streamlit UI → analytics / automata / pattern-mining modules → reproducible CSV data.

### Modules
`automata.py` validates event order; `analytics.py` computes session and customer summaries; `pattern_mining.py` discovers product co-occurrence; `data/generate_data.py` creates seeded synthetic sessions.

### Limitations
The dataset is simulated and cannot represent real shoppers. Product patterns currently use category baskets, not product-level line items. The DFA deliberately simplifies real e-commerce (for example, it does not model payment failures or multiple checkout attempts). KMeans depends on feature scaling and chosen cluster count; cluster IDs do not have inherent meanings.

### Future enhancements
Import real item-level baskets with consent, compare segment stability, add time-series reporting, model returns, and expand the automaton to cover payment and retry paths.
""")
