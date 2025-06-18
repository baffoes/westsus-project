import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from style import *

# Load data
df_results = pd.read_csv("data/ResultsV2.csv", delimiter=";")
df_conditions = pd.read_csv("data/ConditionsV2.csv", delimiter=";")

# Only keep 'start' occasion
df_conditions = df_conditions[df_conditions["Occasion"] == "start"]

# Remove duplicates before merge
df_conditions = df_conditions.drop_duplicates(subset=['Stadium', 'Date', 'Event', 'Race'])

# Merge datasets
df_gekoppeld = pd.merge(df_results, df_conditions, on=['Stadium', 'Date', 'Event', 'Race'], how='left')

# Drop rows with missing data
df_gekoppeld = df_gekoppeld.dropna(subset=[
    'SeasonalBest', 'Country_y', 'Distance', 'Occasion', 'Time_y', 'TempIndoors',
    'TempIce', 'Humidity', 'TempOutdoors', 'AirpressureSealevel', 'AirpressureSurface'
])

# Calculate performance difference and correct it
df_gekoppeld["Verschil_prestatie_SB"] = df_gekoppeld["SeasonalBest"] - df_gekoppeld["Time_x"]
correctie = -5 * df_gekoppeld["Verschil_prestatie_SB"].min()
df_gekoppeld["Verschil_prestatie_SB_correctie"] = df_gekoppeld["Verschil_prestatie_SB"] + correctie

# Fix incorrect ice temperatures (must be <= 0)
df_gekoppeld['TempIce'] = df_gekoppeld['TempIce'].apply(lambda x: -x if x > 0 else x)

# Convert Date
df_gekoppeld['Date'] = pd.to_datetime(df_gekoppeld['Date'], format='%d-%m-%Y')

# Convert 'Date' to Year
df_gekoppeld['Year'] = df_gekoppeld['Date'].dt.year

# Filter out unrealistic performances
df_gekoppeld = df_gekoppeld[df_gekoppeld['Time_x'] < 1.1 * df_gekoppeld['SeasonalBest']]

# --- Initialize Dash app ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "Wetsus Dashboard - Performance Analysis"

# --- Layout ---t 
app.layout = dbc.Container([

    # Header
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1("Speed Skating Performance Analysis", 
                        className="text-center mb-2",
                        style=title_style),
                html.P("Advanced Analytics Dashboard based on ISU Speed Skating Data",
                       className="text-center text-muted mb-4",
                       style=subtitle_style)
            ], style=header_div_style)
        ], width=12)
    ]),

    # Controls Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🎛️ Dashboard Controls", className="card-title mb-3", style=title_style),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Gender:", style=label_style),
                            dcc.Dropdown(
                                id='gender-dropdown',
                                options=[{'label': g, 'value': g} for g in sorted(df_gekoppeld['Gender'].unique())],
                                value='Men',
                                clearable=False,
                                style=dropdown_style
                            )
                        ], width=2),
                        dbc.Col([
                            html.Label("Distance (m):", style=label_style),
                            dcc.Dropdown(
                                id='distance-dropdown',
                                options=[{'label': d, 'value': d} for d in sorted(df_gekoppeld['Distance'].unique())],
                                value=500,
                                clearable=False,
                                style=dropdown_style
                            )
                        ], width=2),
                        dbc.Col([
                            html.Label("Country:", style=label_style),
                            dcc.Dropdown(
                                id='country-dropdown',
                                options=[{'label': c, 'value': c} for c in sorted(df_gekoppeld['Country_x'].unique())],
                                multi=True,
                                placeholder='All countries',
                                style=dropdown_style
                            )
                        ], width=2),
                        dbc.Col([
                            html.Label("Stadium:", style=label_style),
                            dcc.Dropdown(
                                id='stadium-dropdown',
                                options=[{'label': s, 'value': s} for s in sorted(df_gekoppeld['Stadium'].unique())],
                                multi=True,
                                placeholder='All stadiums',
                                style=dropdown_style
                            )
                        ], width=2),
                        dbc.Col([
                            html.Label("Athlete:", style=label_style),
                            dcc.Dropdown(
                                id='athlete-dropdown',
                                options=[],
                                multi=True,
                                placeholder='All athletes',
                                style=dropdown_style
                            )
                        ], width=2),
                        dbc.Col([
                            html.Label("Year Range:", style=label_style),
                            dcc.RangeSlider(
                                id='year-slider',
                                min=df_gekoppeld['Year'].min(),
                                max=df_gekoppeld['Year'].max(),
                                step=1,
                                marks={str(year): {'label': str(year), 'style': slider_marks_style}
                                       for year in range(df_gekoppeld['Year'].min(), df_gekoppeld['Year'].max()+1, 5)},
                                value=[df_gekoppeld['Year'].min(), df_gekoppeld['Year'].max()],
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], width=2)
                    ])
                ])
            ], style=card_style)
        ], width=12)
    ]),

    # Main Chart and Stats
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='temp-time-scatter'),
                    html.Div(id='stats-output', className="mt-3", style=stats_output_style),
                    html.Div([
                        html.Button("📥 Download CSV", id="btn_csv", className="mt-3 btn", style=download_button_style)
                    ], className="text-center"),
                    dcc.Download(id="download-dataframe-csv")
                ])
            ], style=card_style)
        ], width=12)
    ], className="mb-4"),

    # Secondary Charts Row 1
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='time-trend')
                ])
            ], style=card_style)
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='temp-distribution')
                ])
            ], style=card_style)
        ], width=6)
    ], className="mb-4"),

    # Secondary Charts Row 2
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='performance-by-stadium')
                ])
            ], style=card_style)
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='avg-ice-temp-by-stadium')
                ])
            ], style=card_style)
        ], width=6)
    ]),

    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(style={'borderColor': '#2c5aa0', 'margin': '30px 0'}),
            html.P("🏆 Wetsus Performance Analytics Dashboard | Optimizing Athletic Performance Through Data Science",
                   className="text-center text-muted",
                   style=footer_text_style)
        ], width=12)
    ])
], fluid=True, style=main_container_style)

# --- Dependent Athlete Dropdown Callback ---
@app.callback(
    Output('athlete-dropdown', 'options'),
    Output('athlete-dropdown', 'value'),
    Input('gender-dropdown', 'value'),
    Input('distance-dropdown', 'value'),
    Input('year-slider', 'value'),
    Input('country-dropdown', 'value'),
    Input('stadium-dropdown', 'value'),
    State('athlete-dropdown', 'value')
)
def update_athlete_options(selected_gender, selected_distance, selected_years, selected_countries, selected_stadiums, selected_athletes):
    filtered_df = df_gekoppeld[
        (df_gekoppeld['Gender'] == selected_gender) &
        (df_gekoppeld['Distance'] == selected_distance) &
        (df_gekoppeld['Year'] >= selected_years[0]) &
        (df_gekoppeld['Year'] <= selected_years[1])
    ]
    if selected_countries:
        filtered_df = filtered_df[filtered_df['Country_x'].isin(selected_countries)]
    if selected_stadiums:
        filtered_df = filtered_df[filtered_df['Stadium'].isin(selected_stadiums)]
    athlete_options = [{'label': n, 'value': n} for n in sorted(filtered_df['Name'].unique())]
    if not selected_athletes:
        return athlete_options, None
    valid_athletes = [a for a in selected_athletes if a in filtered_df['Name'].unique()]
    return athlete_options, valid_athletes if valid_athletes else None

# --- Main Dashboard Callback ---
@app.callback(
    [
        Output('temp-time-scatter', 'figure'),
        Output('stats-output', 'children'),
        Output('time-trend', 'figure'),
        Output('temp-distribution', 'figure'),
        Output('performance-by-stadium', 'figure'),
        Output('avg-ice-temp-by-stadium', 'figure'),
        Output("download-dataframe-csv", "data"),
    ],
    [
        Input('gender-dropdown', 'value'),
        Input('distance-dropdown', 'value'),
        Input('year-slider', 'value'),
        Input('country-dropdown', 'value'),
        Input('stadium-dropdown', 'value'),
        Input('athlete-dropdown', 'value'),
        Input("btn_csv", "n_clicks"),
    ],
    prevent_initial_call='initial_duplicate'
)
def update_all_figures(selected_gender, selected_distance, selected_years, selected_countries, selected_stadiums, selected_athletes, n_clicks):
    ctx = dash.callback_context
    
  
    # --- Filter data ---
    filtered_df = df_gekoppeld[
        (df_gekoppeld['Gender'] == selected_gender) &
        (df_gekoppeld['Distance'] == selected_distance) &
        (df_gekoppeld['Year'] >= selected_years[0]) &
        (df_gekoppeld['Year'] <= selected_years[1])
    ]
    if selected_countries:
        filtered_df = filtered_df[filtered_df['Country_x'].isin(selected_countries)]
    if selected_stadiums:
        filtered_df = filtered_df[filtered_df['Stadium'].isin(selected_stadiums)]
    if selected_athletes:
        filtered_df = filtered_df[filtered_df['Name'].isin(selected_athletes)]

    if filtered_df.empty:
        empty_fig = px.scatter(title="No data available", template='plotly_dark')
        empty_fig.update_layout(dark_template['layout'])
        return empty_fig, "No data for this selection.", empty_fig, empty_fig, empty_fig, empty_fig, None

    # --- Outlier Calculation ---
    Q1 = filtered_df['Time_x'].quantile(0.25)
    Q3 = filtered_df['Time_x'].quantile(0.75)
    IQR = Q3 - Q1
    outliers = filtered_df[(filtered_df['Time_x'] < Q1 - 1.5*IQR) | (filtered_df['Time_x'] > Q3 + 1.5*IQR)]

    # --- 1. Main Scatter Plot: Temperature vs Time (with outliers) ---
    scatter_fig = px.scatter(
        filtered_df,
        x='TempIce',
        y='Time_x',
        title=f"❄️ Ice Temperature vs Performance Time ({selected_distance}m {selected_gender})",
        labels={'TempIce': 'Ice Temperature (°C)', 'Time_x': 'Time (s)'},
        hover_data=['Name', 'Stadium', 'Date', 'Year'],
        color='Year',
        trendline="lowess",
        color_continuous_scale='Blues'
    )
    if not outliers.empty:
        scatter_fig.add_scatter(
            x=outliers['TempIce'],
            y=outliers['Time_x'],
            mode='markers',
            marker=dict(color='#ff6b6b', size=10, symbol='x'),
            name='Outliers',
            text=outliers['Name']
        )
    scatter_fig.update_layout(dark_template['layout'])
    scatter_fig.update_layout(showlegend=True, title_font_size=16, title_font_color='#87ceeb')

    # --- Stats output ---
    stats_text = html.Div([
        dbc.Row([
            dbc.Col([
                html.H6("📊 Analysis Summary", style={'color': '#87ceeb', 'fontWeight': 'bold', 'marginBottom': '15px'})
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Strong("🚻 Gender: ", style={'color': '#4682b4'}),
                    html.Span(f"{selected_gender}", style={'color': '#ffffff'})
                ], className="mb-2")
            ], width=3),
            dbc.Col([
                html.Div([
                    html.Strong("📏 Distance: ", style={'color': '#4682b4'}),
                    html.Span(f"{selected_distance}m", style={'color': '#ffffff'})
                ], className="mb-2")
            ], width=3),
            dbc.Col([
                html.Div([
                    html.Strong("📅 Years: ", style={'color': '#4682b4'}),
                    html.Span(f"{selected_years[0]}-{selected_years[1]}", style={'color': '#ffffff'})
                ], className="mb-2")
            ], width=3),
            dbc.Col([
                html.Div([
                    html.Strong("📈 Data Points: ", style={'color': '#4682b4'}),
                    html.Span(f"{len(filtered_df)}", style={'color': '#ffffff'})
                ], className="mb-2")
            ], width=3),
        ]),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Strong("⏱️ Avg Time: ", style={'color': '#4682b4'}),
                    html.Span(f"{filtered_df['Time_x'].mean():.2f}s ± {filtered_df['Time_x'].std():.2f}", style={'color': '#ffffff'})
                ], className="mb-2")
            ], width=6),
            dbc.Col([
                html.Div([
                    html.Strong("❄️ Avg Ice Temp: ", style={'color': '#4682b4'}),
                    html.Span(f"{filtered_df['TempIce'].mean():.1f}°C ± {filtered_df['TempIce'].std():.1f}", style={'color': '#ffffff'})
                ], className="mb-2")
            ], width=3),
            dbc.Col([
                html.Div([
                    html.Strong("🔎 Outliers: ", style={'color': '#4682b4'}),
                    html.Span(f"{len(outliers)}", style={'color': '#ff6b6b' if len(outliers) > 0 else '#ffffff'})
                ], className="mb-2")
            ], width=3),
        ])
    ])

    # --- 2. Time Trend by Year ---
    time_trend_fig = px.box(
        filtered_df,
        x='Year',
        y='Time_x',
        title=f"📈 Performance Time Trend by Year ({selected_distance}m {selected_gender})",
        labels={'Time_x': 'Time (s)', 'Year': ''},
        color='Year',
        color_discrete_sequence=['#87ceeb', '#4682b4', '#5f9ea0', '#6495ed']
    )
    time_trend_fig.update_layout(dark_template['layout'])
    time_trend_fig.update_layout(showlegend=False, title_font_size=16, title_font_color='#87ceeb')

    # --- 3. Temperature Distribution ---
    temp_dist_fig = px.histogram(
        filtered_df,
        x='TempIce',
        nbins=20,
        title=f"🌡️ Ice Temperature Distribution ({selected_distance}m {selected_gender})",
        labels={'TempIce': 'Ice Temperature (°C)'},
        marginal='box',
        color_discrete_sequence=['#4682b4']
    )
    temp_dist_fig.update_layout(dark_template['layout'])
    temp_dist_fig.update_layout(title_font_size=16, title_font_color='#87ceeb')

    # --- 4. Performance by Stadium ---
    stadium_fig = px.box(
        filtered_df,
        x='Stadium',
        y='Time_x',
        title=f"🏟️ Performance by Stadium ({selected_distance}m {selected_gender})",
        labels={'Time_x': 'Time (s)'},
        color='Stadium',
        color_discrete_sequence=['#87ceeb', '#4682b4', '#5f9ea0', '#6495ed', '#00bfff', '#1e90ff']
    )
    stadium_fig.update_layout(dark_template['layout'])
    stadium_fig.update_layout(xaxis={'categoryorder':'total descending'}, showlegend=False, title_font_size=16, title_font_color='#87ceeb')
    stadium_fig.update_xaxes(tickangle=45)

    # --- 5. Average Ice Temperature by Stadium ---
    avg_temp_df = filtered_df.groupby('Stadium')['TempIce'].mean().reset_index().sort_values('TempIce', ascending=False)
    avg_temp_fig = px.bar(
        avg_temp_df,
        x='Stadium',
        y='TempIce',
        title=f"🏟️ Average Ice Temperature by Stadium ({selected_distance}m {selected_gender})",
        labels={'TempIce': 'Average Ice Temperature (°C)'},
        color='TempIce',
        color_continuous_scale='Blues'
    )
    avg_temp_fig.update_layout(dark_template['layout'])
    avg_temp_fig.update_layout(xaxis={'categoryorder':'total descending'}, title_font_size=16, title_font_color='#87ceeb')
    avg_temp_fig.update_xaxes(tickangle=45)

    # --- 6. Download CSV if requested ---
    triggered = [t['prop_id'] for t in ctx.triggered][0]
    if "btn_csv" in triggered:
        return scatter_fig, stats_text, time_trend_fig, temp_dist_fig, stadium_fig, avg_temp_fig, dcc.send_data_frame(filtered_df.to_csv, "filtered_data.csv")
    else:
        return scatter_fig, stats_text, time_trend_fig, temp_dist_fig, stadium_fig, avg_temp_fig, None

# --- Run app ---
if __name__ == '__main__':
    app.run(debug=True)