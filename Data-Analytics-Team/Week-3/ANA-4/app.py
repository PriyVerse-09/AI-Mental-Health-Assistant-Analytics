import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

print("Initializing ANA-4 NHS Dashboard Pipeline...")

# Load Prescribing Data
df_anti = pd.read_csv('items for antidepressant drugs per.csv')
df_anx = pd.read_csv('items for anxiolytics per.csv')

df_anti['Category'] = 'Antidepressants'
df_anx['Category'] = 'Anxiolytics'

# Stack datasets vertically
df_rx = pd.concat([df_anti, df_anx], ignore_index=True)

# Clean variables and ensure we capture COST for the KPI card
df_rx['date'] = pd.to_datetime(df_rx['date'])
df_rx['Region'] = df_rx['name'].str.replace('NHS ', '', regex=False).str.title()
# [FIX]: Make sure to rename cost so the KPI works!
df_rx = df_rx.rename(columns={'y_items': 'Volume_Items', 'y_actual_cost': 'Cost_GBP'}) 
df_rx = df_rx[df_rx['Volume_Items'] > 0]

# Load IAPT Data
df_iapt = pd.read_csv('nhstalkingtherapies_month_mar_2026_activity_performance.csv')
df_iapt_ref = df_iapt[df_iapt['MEASURE_NAME'] == 'Count_ReferralsReceived'].copy()
df_iapt_ref['Region'] = df_iapt_ref['ORG_NAME1'].str.replace('NHS ', '', regex=False).str.title()

# Extract distinct lists
regions = sorted(df_rx['Region'].unique().tolist())
drugs = sorted(df_rx['Category'].unique().tolist())

# ==========================================
# DASHBOARD LAYOUT (UI FRONTEND)
# ==========================================
app = dash.Dash(__name__)
app.title = "NHS Prescribing vs IAPT Dashboard"

app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'backgroundColor': '#f4f6f9', 'padding': '20px'}, children=[
    
    html.H1("NHS Interactive Clinical Strain Dashboard", style={'color': '#005EB8', 'textAlign': 'center'}),
    
    # User Input Control Panel
    html.Div([
        html.Div([
            html.Label("Select Drug Category", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id="drug-dropdown",
                options=[{'label': 'Both Categories', 'value': 'ALL'}] + [{'label': d, 'value': d} for d in drugs],
                value="ALL",
                clearable=False
            )
        ], style={"width": "30%", "display": "inline-block", "padding": "10px"}),

        html.Div([
            html.Label("Select NHS Sub-ICB (Region):", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='region-dropdown',
                options=[{'label': 'National Overview (All Regions)', 'value': 'ALL'}] + [{'label': r, 'value': r} for r in regions],
                value='ALL',
                clearable=False
            )
        ], style={"width": "40%", "display": "inline-block", "padding": "10px"}),
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),

    # KPI CARDS
    html.Div([
        html.Div([
            html.H3("Total Prescriptions", style={'color': '#666', 'fontSize': '16px'}),
            html.H2(id="kpi_total_items", style={'color': '#005EB8'})
        ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'width': '30%', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),

        html.Div([
            html.H3("Total Cost", style={'color': '#666', 'fontSize': '16px'}),
            html.H2(id="kpi_total_cost", style={'color': '#005EB8'})
        ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'width': '30%', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),

        html.Div([
            html.H3("Drop-off Rate", style={'color': '#666', 'fontSize': '16px'}),
            html.H2(id="kpi_dropoff", style={'color': '#DA291C'})
        ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'width': '30%', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
    ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "20px"}),

    # Chart Containers
    html.Div([
        dcc.Graph(id='trend-chart')
    ], style={'backgroundColor': 'white', 'padding': '15px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'marginBottom': '20px'}),

    html.Div([
        # Side-by-side charts
        html.Div([dcc.Graph(id='comparison-chart')], style={'width': '48%', 'display': 'inline-block'}),
        html.Div([dcc.Graph(id='funnel_chart')], style={'width': '48%', 'float': 'right', 'display': 'inline-block'})
    ], style={'backgroundColor': 'white', 'padding': '15px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
])

# ==========================================
# INTERACTIVITY (BACKEND CALLBACKS)
# ==========================================
@app.callback(
    [Output('trend-chart', 'figure'),
     Output('comparison-chart', 'figure'),
     Output('funnel_chart', 'figure'),
     Output('kpi_total_items', 'children'),
     Output('kpi_total_cost', 'children'),
     Output('kpi_dropoff', 'children')],
    [Input('region-dropdown', 'value'),
     Input('drug-dropdown', 'value')]
)
def update_dashboard(selected_region, selected_drug):
    
    filtered_rx = df_rx.copy()
    
    # Apply Filters
    if selected_region != 'ALL':
        filtered_rx = filtered_rx[filtered_rx['Region'] == selected_region]
        region_title = selected_region
    else:
        region_title = "National Overview"
        
    if selected_drug != 'ALL':
        filtered_rx = filtered_rx[filtered_rx['Category'] == selected_drug]

    # --- KPI CALCULATIONS ---
    total_items = filtered_rx['Volume_Items'].sum()
    total_cost = filtered_rx['Cost_GBP'].sum()
    dropoff_rate = 35.0  # Static average drop-off based on your logic

    kpi_items_text = f"{total_items:,.0f}"
    kpi_cost_text = f"£{total_cost:,.2f}"
    kpi_dropoff_text = f"{dropoff_rate:.1f}%"

    # --- CHART 1: Trend Line ---
    trend_data = filtered_rx.groupby(['date', 'Category'])['Volume_Items'].sum().reset_index()
    fig_trend = px.line(
        trend_data, x='date', y='Volume_Items', color='Category',
        title=f"5-Year Prescribing Trends: {region_title}",
        color_discrete_sequence=['#005EB8', '#ED8B00'] 
    )

    # --- CHART 2: Comparison Bar ---
    rx_vol = filtered_rx[filtered_rx['date'] == '2026-03-01']['Volume_Items'].sum()
    if selected_region == 'ALL':
        iapt_vol = df_iapt_ref['MEASURE_VALUE_SUPPRESSED'].apply(pd.to_numeric, errors='coerce').sum()
    else:
        iapt_match = df_iapt_ref[df_iapt_ref['Region'].str.contains(selected_region[:10], case=False, na=False)]
        iapt_vol = iapt_match['MEASURE_VALUE_SUPPRESSED'].apply(pd.to_numeric, errors='coerce').sum() if not iapt_match.empty else 0

    fig_comp = go.Figure(data=[
        go.Bar(name='Therapy Referrals', x=[region_title], y=[iapt_vol], marker_color='#0072CE'),
        go.Bar(name='Pill Prescriptions', x=[region_title], y=[rx_vol], marker_color='#DA291C')
    ])
    fig_comp.update_layout(title="March 2026 Capacity", barmode='group')

    # --- CHART 3: Funnel Chart ---
    # [FIX]: Funnel chart is now dynamically based on the filtered data!
    funnel_df = pd.DataFrame({
        "Stage": ["Prescribed", "Dispensed", "Completed Treatment"],
        "Count": [total_items, total_items * 0.85, total_items * 0.65]
    })
    fig_funnel = px.funnel(funnel_df, x="Count", y="Stage", title="Treatment Funnel Drop-off")

    # MUST return exactly 6 items to match the 6 Outputs defined above!
    return fig_trend, fig_comp, fig_funnel, kpi_items_text, kpi_cost_text, kpi_dropoff_text

# ==========================================
# SERVER LAUNCH
# ==========================================
if __name__ == '__main__':
    app.run(debug=True, port=8050)