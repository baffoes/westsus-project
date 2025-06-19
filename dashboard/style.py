# Custom CSS styling

# styles.py

main_container_style = {'backgroundColor': '#0a1428'}

header_div_style = {
    'background': 'linear-gradient(135deg, #1e3a5f 0%, #0a1428 100%)',
    'padding': '30px',
    'borderRadius': '15px',
    'marginBottom': '20px'
}

title_style = {
    'color': '#87ceeb',
    'fontWeight': 'bold',
    'textShadow': '2px 2px 4px rgba(0,0,0,0.5)'
}

subtitle_style = {
    'color': '#b0c4de',
    'fontSize': '18px'
}

dropdown_style = {
    'backgroundColor': '#0a1428',
    'color': '#000000'
}

label_style = {
    'color': '#ffffff',
    'fontWeight': 'bold'
}

slider_marks_style = {
    'color': '#87ceeb'
}

stats_output_style = {
    'backgroundColor': '#0f2142',
    'padding': '15px',
    'borderRadius': '8px',
    'border': '1px solid #2c5aa0'
}

download_button_style = {
    'backgroundColor': '#2c5aa0',
    'color': 'white',
    'border': 'none',
    'padding': '10px 20px',
    'borderRadius': '5px',
    'fontWeight': 'bold'
}

footer_text_style = {
    'color': '#87ceeb',
    'fontSize': '14px',
    'fontStyle': 'italic'
}

custom_style = {
    'backgroundColor': '#0a1428',
    'color': '#ffffff',
    'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
}

card_style = {
    'backgroundColor': '#1e3a5f',
    'border': '1px solid #2c5aa0',
    'borderRadius': '10px',
    'padding': '20px',
    'margin': '10px 0',
    'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.3)'
}
  # Dark theme template for all plots
dark_template = {
        'layout': {
            'paper_bgcolor': '#1e3a5f',
            'plot_bgcolor': '#0f2142',
            'font': {'color': '#ffffff'},
            'colorway': ['#87ceeb', '#4682b4', '#5f9ea0', '#6495ed', '#00bfff', '#1e90ff', '#4169e1', '#0000cd'],
            'xaxis': {'gridcolor': '#2c5aa0', 'zerolinecolor': '#2c5aa0'},
            'yaxis': {'gridcolor': '#2c5aa0', 'zerolinecolor': '#2c5aa0'}
        }
    }

# Graph styling template
graph_layout_style = {
    'paper_bgcolor': '#1e3a5f',
    'plot_bgcolor': '#0f2142',
    'font': dict(color='white'),
    'xaxis': dict(
        gridcolor='#2c5aa0',
        zerolinecolor='#2c5aa0',
        title_font=dict(color='white')
    ),
    'yaxis': dict(
        gridcolor='#2c5aa0',
        zerolinecolor='#2c5aa0',
        title_font=dict(color='white')
    ),
    'legend': dict(
        font=dict(color='white'),
        bgcolor='rgba(30, 58, 95, 0.8)'
    ),
    'title_font': dict(color='white')
}

# Marker styling
marker_style = {
    'size': 8,
    'opacity': 0.7,
    'line': dict(width=1, color='white')
}
    