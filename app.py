import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import io
import base64
import plotly.express as px
import asyncio
from checker import main

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    dcc.Textarea(
        id='url-input',
        placeholder='Enter URLs separated by newlines...',
        style={'width': '100%', 'height': 200},
    ),
    html.Br(),
    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload File'),
        multiple=False
    ),
    html.Button('Submit', id='submit-button', n_clicks=0),
    html.Div(id='output-data-upload'),
    dcc.Graph(id='pie-chart')
])


def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            return df.iloc[:, 0].tolist()  # Assume URLs are in the first column
        elif 'txt' in filename:
            # Process TXT file
            return decoded.decode('utf-8').splitlines()
    except Exception as e:
        print(e)
        return []

@app.callback(
    Output('output-data-upload', 'children'),
    Output('pie-chart', 'figure'),
    Input('submit-button', 'n_clicks'),
    State('url-input', 'value'),
    State('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_output(n_clicks, url_input, uploaded_file_contents, uploaded_file_name):
    if n_clicks > 0:
        urls = []
        if uploaded_file_contents is not None:
            urls += parse_contents(uploaded_file_contents, uploaded_file_name)
        if url_input is not None:
            urls += url_input.splitlines()

        if urls:
            results = asyncio.run(main(urls))

            # Filter out any None or Timeout results
            filtered_results = [result for result in results if result is not None and result[1] != "Timeout"]

            df = pd.DataFrame(filtered_results, columns=["URL", "Indexed"])

            table = dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in df.columns],
                export_format="csv",
            )

            pie_chart = px.pie(df, names='Indexed', title='Percentage of Indexed vs Non-Indexed URLs')

            return table, pie_chart

    return dash.no_update, dash.no_update


if __name__ == '__main__':
    app.run_server(debug=True)