import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Styles
main_container_style = {'backgroundColor': '#0a1428'}
header_div_style = {
    'background': 'linear-gradient(135deg, #1e3a5f 0%, #0a1428 100%)',
    'padding': '30px',
    'borderRadius': '15px',
    'marginBottom': '20px'
}
title_style = {'color': '#87ceeb', 'fontWeight': 'bold', 'textShadow': '2px 2px 4px rgba(0,0,0,0.5)'}
dropdown_style = {'backgroundColor': '#1e3a5f', 'color': "#131212", 'border': '1px solid #2c5aa0'}
graph_container_style = {
    'backgroundColor': '#0f2142',
    'padding': '15px',
    'borderRadius': '15px',
    'margin': '20px 0',
    'border': '1px solid #2c5aa0'
}

# Data laden en voorbereiden
try:
    df_results = pd.read_csv("data/ResultsV2.csv", delimiter=";")
    df_conditions = pd.read_csv("data/ConditionsV2.csv", delimiter=";")
    df_conditions = df_conditions[df_conditions["Occasion"] == "start"]
    df_conditions = df_conditions.drop_duplicates(subset=['Stadium', 'Date', 'Event', 'Race'])
    df_gekoppeld = pd.merge(df_results, df_conditions, on=['Stadium', 'Date', 'Event', 'Race'], how='left')
    df_gekoppeld = df_gekoppeld.dropna(subset=[
        'SeasonalBest', 'Country_y', 'Distance', 'Occasion', 'Time_y', 'TempIndoors',
        'TempIce', 'Humidity', 'TempOutdoors', 'AirpressureSealevel', 'AirpressureSurface'
    ])
    df_gekoppeld["Verschil_prestatie_SB"] = df_gekoppeld["SeasonalBest"] - df_gekoppeld["Time_x"]
    correctie = -5 * df_gekoppeld["Verschil_prestatie_SB"].min()
    df_gekoppeld["Verschil_prestatie_SB_correctie"] = df_gekoppeld["Verschil_prestatie_SB"] + correctie
    df_gekoppeld['TempIce'] = df_gekoppeld['TempIce'].apply(lambda x: -x if x > 0 else x)
    df_gekoppeld['Date'] = pd.to_datetime(df_gekoppeld['Date'], format='%d-%m-%Y')
    df_gekoppeld['Year'] = df_gekoppeld['Date'].dt.year
    df_gekoppeld['Gender_num'] = df_gekoppeld['Gender'].map({'Man': 0, 'Woman': 1})
        # More flexible gender mapping
    df_gekoppeld['Gender_clean'] = df_gekoppeld['Gender'].astype(str).str.lower().str.strip()

    # Try multiple mapping approaches
    gender_mapping = {
        'man': 1, 'woman': 0,
        'male': 1, 'female': 0,
        'm': 1, 'f': 0, 'w': 0,
        'men': 1, 'women': 0,
        'masculine': 1, 'feminine': 0
    }
    
    df_gekoppeld['Gender_num'] = df_gekoppeld['Gender_clean'].map(gender_mapping)
    
    # Check mapping results
    unmapped_genders = df_gekoppeld[df_gekoppeld['Gender_num'].isna()]['Gender_clean'].unique()
    if len(unmapped_genders) > 0:
        print(f"Unmapped gender values: {unmapped_genders}")
        # Fill unmapped values with a default (0 for woman, 1 for man)
        # You might need to adjust this based on your actual data
        df_gekoppeld['Gender_num'] = df_gekoppeld['Gender_num'].fillna(0)

    data = df_gekoppeld[df_gekoppeld['Time_x'] < 1.1 * df_gekoppeld['SeasonalBest']].copy()

    def bereken_schaatsprestatie(row):
        denominator = (
            1.662e-11 + -5.078e-09 + 8.492e-09 + 
            3.362e-09 * row['Gender_num'] + 
            1.218e-09 * row['Lane'] + 
            1.374e-12 * row['EstimatedTFM'] + 
            8.312e-09 * row['Distance'] + 
            -1.871e-10 * row['TempIndoors'] + 
            1.08e-09 * row['TempIce'] + 
            6.49e-12 * row['Humidity'] + 
            1.985e-10 * row['AirpressureSurface']
        )
        y = 1 / (denominator ** 0.5)
        y = y - 480.25
        return row['SeasonalBest'] - y

    # Voeg kolom schaatsprestatie toe
    data['schaatsprestatie'] = data.apply(bereken_schaatsprestatie, axis=1)
    
    # Unieke afstanden voor dropdown
    distance_options = [{'label': str(int(d)), 'value': d} for d in sorted(data['Distance'].unique())]
    
except Exception as e:
    print(f"Fout bij het laden van de data: {e}")
    data = pd.DataFrame()

# Dash app initialiseren
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.Div([
        html.H1("Schaatsprestaties Dashboard", style=title_style)
    ], style=header_div_style),

    dbc.Row([
        dbc.Col([
            html.Label("Selecteer Distance:", style={'color': 'white'}),
            dcc.Dropdown(
                id='distance-dropdown',
                options=distance_options,
                value=distance_options[0]['value'] if distance_options else 500,
                clearable=False,
                style=dropdown_style
            ),
        ], width=4),
    ], style={'marginBottom': '20px'}),

    # Add data info row
    dbc.Row([
        dbc.Col([
            html.Div(id='data-info', style={'color': 'white', 'marginBottom': '10px'})
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dcc.Graph(id='performance-graph', style={'height': '600px'})
        ])
    ], style=graph_container_style),

], fluid=True, style=main_container_style)

# Callback om grafiek te updaten
@app.callback(
    [Output('performance-graph', 'figure'),
     Output('data-info', 'children')],
    Input('distance-dropdown', 'value')
)
def update_graph(selected_distance):
    filtered = data[data['Distance'] == selected_distance]
    
    # Data info
    info_text = f"Aantal datapunten voor {selected_distance}m: {len(filtered)}"
    
    if len(filtered) == 0:
        # Create empty figure if no data
        fig = go.Figure()
        fig.add_annotation(
            text="Geen data beschikbaar voor deze afstand",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(color="white", size=16)
        )
        fig.update_layout(
            paper_bgcolor='#1e3a5f',
            plot_bgcolor='#0f2142',
            font=dict(color='white'),
            title=f'Schaatsprestaties voor afstand {selected_distance} meter'
        )
        return fig, info_text

    # Create scatter plot with explicit styling
    fig = px.scatter(
        filtered,
        x='Time_x',
        y='schaatsprestatie',
        color='Gender',
        labels={
            'Time_x': 'Tijd (seconds)',
            'schaatsprestatie': 'Schaatsprestatie'
        },
        title=f'Schaatsprestaties voor afstand {selected_distance} meter',
        color_discrete_map={'man': '#87ceeb', 'woman': '#ff6b6b'}  # Explicit colors
    )
    
    # Update layout with better visibility
    fig.update_layout(
        paper_bgcolor='#1e3a5f',
        plot_bgcolor='#0f2142',
        font=dict(color='white'),
        xaxis=dict(
            gridcolor='#2c5aa0',
            zerolinecolor='#2c5aa0',
            title_font=dict(color='white')
        ),
        yaxis=dict(
            gridcolor='#2c5aa0',
            zerolinecolor='#2c5aa0',
            title_font=dict(color='white')
        ),
        legend=dict(
            font=dict(color='white'),
            bgcolor='rgba(30, 58, 95, 0.8)'
        ),
        title_font=dict(color='white')
    )
    
    # Make sure markers are visible
    fig.update_traces(
        marker=dict(
            size=8,
            opacity=0.7,
            line=dict(width=1, color='white')
        )
    )
    
    return fig, info_text


if __name__ == '__main__':
    app.run(debug=True)