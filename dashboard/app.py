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

# Add Gender_num column for calculation
df_gekoppeld['Gender_num'] = df_gekoppeld['Gender'].map({'Men': 0, 'Women': 1})

# Function to calculate schaatsprestatie
def bereken_schaatsprestatie(row):
    denominator = None
    if row['Distance'] == 500:
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
        
    elif row['Distance'] == 1000:
        denominator = (
            4.29e-12 +  1.212e-08 + 3.763e-09 + 
            9.894e-09 * row['Gender_num'] - 
            2.579e-09 * row['Lane'] + 
            1.763e-12 * row['EstimatedTFM'] + 
            4.29e-09 * row['Distance'] + 
            5.413e-10 * row['TempIndoors'] + 
            1.559e-09 * row['TempIce'] - 
            1.162e-10 * row['Humidity'] + 
            6.082e-11 * row['AirpressureSurface']
        )
    elif row['Distance'] == 1500:
        denominator = (
            1.812e-12 - 1.04e-09 + 2.483e-08 +
            1.147e-08 * row['Gender_num'] +
            3.702e-09 * row['Lane'] +
            4.794e-12 * row['EstimatedTFM'] +
            2.718e-09 * row['Distance'] +
            -2.122e-09 * row['TempIndoors'] +
            -1.171e-09 * row['TempIce'] +
            -1.136e-09 * row['Humidity'] +
            3.257e-10 * row['AirpressureSurface']
        )
    elif row['Distance'] == 3000:
        denominator = (
            4.126e-13 - 3.063e-09 + 4.054e-08 +
            6.188e-08 * row['Gender_num'] +
            1.044e-08 * row['Lane'] +
            -5.195e-13 * row['EstimatedTFM'] +
            1.238e-09 * row['Distance'] +
            2.952e-10 * row['TempIndoors'] +
            3.25e-09 * row['TempIce'] +
            -1.502e-10 * row['Humidity'] +
            6.038e-10 * row['AirpressureSurface']
        )
    elif row['Distance'] == 5000:
        denominator = (
             1.582e-13 + 7.289e-08 + 3.185e-09 +
            -5.162e-08 * row['Gender_num'] +
            7.835e-08 * row['Lane'] +
            5.687e-13 * row['EstimatedTFM'] +
            7.909e-10 * row['Distance'] +
            1.577e-09 * row['TempIndoors'] +
            1.809e-08 * row['TempIce'] +
            -6.303e-10 * row['Humidity'] +
            5.537e-10 * row['AirpressureSurface']
        )
    elif row['Distance'] == 10000:
        denominator = (
            4.29e-12 + 1.212e-08 + 3.763e-09 + 
            9.894e-09 * row['Gender_num'] + 
            -2.579e-09 * row['Lane'] + 
            1.763e-12 * row['EstimatedTFM'] + 
            4.29e-09 * row['Distance'] + 
            5.413e-10 * row['TempIndoors'] + 
            1.559e-09 * row['TempIce'] - 
            1.162e-10 * row['Humidity'] + 
            6.082e-11 * row['AirpressureSurface']
        )
    else:
        return None

    y = 1 / (denominator ** 0.5)
    y = round(y - 480.25, 2)
    return row['SeasonalBest'] - y


# Add schaatsprestatie column
df_gekoppeld['schaatsprestatie'] = df_gekoppeld.apply(bereken_schaatsprestatie, axis=1)

# --- Initialize Dash app ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "Speedskating Dashboard"

# --- Layout ---t 
app.layout = dbc.Container([

    # Header
    
    dbc.Row([
        
        dbc.Col([
            html.Div([
                html.H1("Speedskating Performance Analysis", 
                        className="text-center mb-2",
                        style=title_style),
                html.P("Advanced Analytics Dashboard based on ISU Speedskating Data",
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
                                value=['Men','Women'],
                                multi=True,
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
                                options=[{'label': c, 'value': c} for c in sorted(df_gekoppeld['Country_y'].unique())],
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
                        html.Button("Download CSV", id="btn_csv", className="mt-3 btn", style=download_button_style)
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
    
    # Additional Section 

   dbc.Row([
     dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.H4("Predicted Skating Performance Analysis", 
                            className="text-center mb-2",
                            style=title_style),
                   html.P(
                           "This formula predicts skating performance based on various factors such as gender, "
                            "lane position, the estimated time since the last ice resurfacing, distance, ice and rink temperature, "
                            "humidity, and air pressure. Each variable contributes to the final prediction of skating performance.",
                        className="text-center text-muted mb-4",
                        style=subtitle_style
                        ) 

                ], style=header_div_style),

                dbc.Row([
                    dbc.Col([
                        html.Label("Select Distance:", style=label_style),
                        dcc.Dropdown(
                            id='distance-dropdown-additional',
                            options=[{'label': d, 'value': d} for d in sorted(df_gekoppeld['Distance'].unique())],
                            value=sorted(df_gekoppeld['Distance'].unique())[0] if len(df_gekoppeld['Distance'].unique()) > 0 else 500,
                            clearable=False,
                            style=dropdown_style
                        ),
                    ], width=4),

                    dbc.Col([
                        html.Label("Select Stadium:", style={'color': 'white'}),
                        dcc.Dropdown(
                            id='Stadium-dropdown',
                            options=[{'label': 'All Stadiums', 'value': 'All'}] + 
                                    [{'label': s, 'value': s} for s in sorted(df_gekoppeld['Stadium'].dropna().unique())],
                            value='All',
                            clearable=False,
                            style=dropdown_style
                        ),
                    ], width=4),

                    dbc.Col([
                        html.Div(id='data-info', style=card_style)
                    ], width=4)
                ], style=card_style)
            ])
        ], style=card_style)
    ], width=12)
  ]),

    
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='performance-graph', style={'height': '600px'})
        ])
    ], style={'marginBottom': '20px'}),

    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(style={'borderColor': '#2c5aa0', 'margin': '30px 0'}),
            html.P("Speedskating Performance Analytics Dashboard | Optimizing Athletic Performance Through Data Science",
                   className="text-center text-muted",
                   style=footer_text_style)
        ], width=12)
    ])
], fluid=True, style=main_container_style)

@app.callback(
    Output('stadium-dropdown', 'options'),
    Output('stadium-dropdown', 'value'),
    Input('country-dropdown', 'value'),
    State('stadium-dropdown', 'value')
)
#    Update stadium dropdown options based on selected countries
def update_stadium_options(selected_countries, selected_stadiums):

    if selected_countries:
        # Filter stadiums based on selected countries
        filtered_df = df_gekoppeld[df_gekoppeld['Country_y'].isin(selected_countries)]
        stadium_options = [{'label': s, 'value': s} for s in sorted(filtered_df['Stadium'].unique())]
        
        # Keep only valid stadiums that exist in the filtered countries
        if selected_stadiums:
            valid_stadiums = [s for s in selected_stadiums if s in filtered_df['Stadium'].unique()]
            return stadium_options, valid_stadiums if valid_stadiums else None
        else:
            return stadium_options, None
    else:
        # Show all stadiums when no countries are selected
        stadium_options = [{'label': s, 'value': s} for s in sorted(df_gekoppeld['Stadium'].unique())]
        return stadium_options, selected_stadiums

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
        df_gekoppeld['Gender'].isin(selected_gender) &
        (df_gekoppeld['Distance'] == selected_distance) &
        (df_gekoppeld['Year'] >= selected_years[0]) &
        (df_gekoppeld['Year'] <= selected_years[1])
    ]
    if selected_countries:
        filtered_df = filtered_df[filtered_df['Country_y'].isin(selected_countries)]
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
         df_gekoppeld['Gender'].isin(selected_gender) &
        (df_gekoppeld['Distance'] == selected_distance) &
        (df_gekoppeld['Year'] >= selected_years[0]) &
        (df_gekoppeld['Year'] <= selected_years[1])
    ]
    if selected_countries:
        filtered_df = filtered_df[filtered_df['Country_y'].isin(selected_countries)]
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
    
    if isinstance(selected_gender, list):
     if selected_gender == ['Men']:
        gender_display = "Men"
     elif selected_gender == ['Women']:
        gender_display = "Women"
     elif set(selected_gender) == {'Men', 'Women'}:
        gender_display = "Men & Women"

    # --- 1. Main Scatter Plot: Temperature vs Time (with outliers) ---
    scatter_fig = px.scatter(
        filtered_df,
        x='TempIce',
        y='Time_x',
        title=f"❄️ Ice Temperature vs Performance Time ({selected_distance}m {gender_display})",
        labels={'TempIce': 'Ice Temperature (°C)', 'Time_x': 'Performance Time (s)'},
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
                    html.Span(f"{gender_display}", style={'color': '#ffffff'})
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
        title=f"📈 Performance Time Trend by Year ({selected_distance}m {gender_display})",
        labels={'Time_x': 'Performance Time (s)', 'Year': ''},
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
        title=f"🌡️ Ice Temperature Distribution ({selected_distance}m {gender_display})",
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
        title=f"🏟️ Performance by Stadium ({selected_distance}m {gender_display})",
        labels={'Time_x': 'Performance Time (s)'},
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
        title=f"🏟️ Average Ice Temperature by Stadium ({selected_distance}m {gender_display})",
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

# Callback om grafiek te updaten
@app.callback(
    [Output('performance-graph', 'figure'),
     Output('data-info', 'children')],
    [Input('distance-dropdown-additional', 'value'),
     Input('Stadium-dropdown', 'value')]
)

def update_graph(selected_distance, selected_stadium):
    # Filter op afstand
    filtered = df_gekoppeld[df_gekoppeld['Distance'] == selected_distance]
    
    # Als een specifiek stadion is gekozen, filter daar ook op
    if selected_stadium != 'All':
        filtered = filtered[filtered['Stadium'] == selected_stadium]
    
    # Info tekst
    stadium_info = selected_stadium if selected_stadium != 'All' else "all stadiums"
    info_text = f"Count of datapoints for {selected_distance}m in {stadium_info}: {len(filtered)}"
    
    # Geen data
    if len(filtered) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="Geen data beschikbaar voor deze selectie",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(color="white", size=16)
        )
        fig.update_layout(
            paper_bgcolor='#1e3a5f',
            plot_bgcolor='#0f2142',
            font=dict(color='white'),
            title=f'Predicted Skating Performance for {selected_distance} meter in {stadium_info}'
        )
        return fig, info_text

    # Hoofdplot: scatterplot van voorspelling versus echte tijd
    fig = px.scatter(
    filtered,
    x='Time_x',
    y='schaatsprestatie',
    labels={
        'Time_x': 'Performance Time (seconds)',
        'schaatsprestatie': 'Predicted Skating Performance (seconds)'
    },
    trendline="ols",
    title=f'Predicted Skating Performance for {selected_distance} meter in {stadium_info}',
    hover_data=['Name', 'Gender']  # Hier voeg je toe wat je wilt tonen bij hover
   )

    # Layout en stijl
    fig.update_layout(graph_layout_style)
    fig.update_traces(marker=marker_style)

    return fig, info_text

# --- Run app ---
if __name__ == '__main__':
    app.run(debug=True)