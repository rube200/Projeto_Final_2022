import pandas as pd
import plotly.express as px
from dash import html, dcc

df = pd.DataFrame({
    'Days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday', 'Tuesday',
             'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
    # 'Days': [['Monday', 4], ['Tuesday', 1], ['Wednesday', 2], ['Thursday', 2], ['Friday', 3], ['Saturday', 5], ['Sunday', 9]],
    'Score': [4, 1, 2, 2, 3, 5, 9, 3, 2, 3, 2, 7, 4, 1],
    'Colours': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Last Week\'s Average',
                'Last Week\'s Average', 'Last Week\'s Average', 'Last Week\'s Average', 'This Week\'s Average',
                'This Week\'s Average', 'This Week\'s Average'],
})

fig = px.bar(df, x='Days', y='Score', color='Colours', barmode='group')

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),
    html.Div(children='Dash: A web application framework for your data.'),
    dcc.Graph(
        id='example-graph',
        figure=fig
    )
])