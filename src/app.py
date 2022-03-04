import pandas as pd
import altair as alt
from altair import datum
from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
from datetime import date

alt.data_transformers.disable_max_rows()

##import and wrangle data
raw_trees = pd.read_csv("data/processed_trees.csv")
raw_trees["BLOOM_START"] = pd.to_datetime(raw_trees["BLOOM_START"], format="%d/%m/%Y")
raw_trees["BLOOM_END"] = pd.to_datetime(raw_trees["BLOOM_END"], format="%d/%m/%Y")

# Vancouver geojson
url_geojson = "https://raw.githubusercontent.com/UBC-MDS/cherry_blossom_tracker/main/data/vancouver.geojson"
data_geojson_remote = alt.Data(
    url=url_geojson, format=alt.DataFormat(property="features", type="json")
)

# Build Front End
app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.layout = html.Div(
    [
        dbc.Container(
            html.H1("Vancouver cherry blossom tracker"),
            style={
                "color": "white",
                "background-color": "orchid",
                "font-family": "Helvetica",
            },
        ),
        dbc.Container(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dcc.DatePickerRange(
                                id="picker_date",
                                min_date_allowed=date(2022, 1, 1),
                                max_date_allowed=date(2022, 5, 30),
                                start_date_placeholder_text="Start Period",
                                end_date_placeholder_text="End Period",
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.Label(
                                ["Neighbourhood"], style={"font-weight": "bold"}
                            ),
                            dcc.Dropdown(
                                id="filter_neighbourhood",
                                value="all_neighbourhoods",
                                options=[
                                    {
                                        "label": "All neighbourhoods",
                                        "value": "all_neighbourhoods",
                                    }
                                ]
                                + [
                                    {"label": i, "value": i}
                                    for i in raw_trees.NEIGHBOURHOOD_NAME.unique()
                                ],
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Label(
                                ["Cherry tree cultivars"], style={"font-weight": "bold"}
                            ),
                            dcc.Dropdown(
                                id="filter_cultivar",
                                value="all_cultivars",
                                options=[
                                    {"label": "All cultivars", "value": "all_cultivars"}
                                ]
                                + [
                                    {"label": i, "value": i}
                                    for i in raw_trees.CULTIVAR_NAME.unique()
                                ],
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Label(
                                ["Cherry tree diameter"], style={"font-weight": "bold"}
                            ),
                            dcc.RangeSlider(
                                id="slider_diameter",
                                min=0,
                                max=150,
                                value=[0, 150],
                                marks={0: "0cm", 150: "150cm"},
                                tooltip={"placement": "bottom", "always_visible": True},
                            ),
                        ]
                    ),
                ]
            ),
            style={"background-color": "whitesmoke"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Iframe(
                            id="bar",
                            style={
                                "border-width": "0",
                                "width": "100%",
                                "height": "800px",
                            },
                        )
                    ]
                ),
                dbc.Col(
                    [
                        html.Iframe(
                            id="timeline",
                            style={
                                "border-width": "0",
                                "width": "100%",
                                "height": "100%",
                            },
                        )
                    ]
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Iframe(
                            id="density",
                            style={
                                "border-width": "0",
                                "width": "100%",
                                "height": "800px",
                            },
                        )
                    ]
                ),
                dbc.Col(dcc.Graph(id="map")),
            ]
        ),
    ]
)


def street_map(df):
    map_plot = px.scatter_mapbox(
        df,
        lat="lat",
        lon="lon",
        color_discrete_sequence=["fuchsia"],
        zoom=10.8,
        height=700,
    )
    map_plot.update_layout(mapbox_style="open-street-map")

    return map_plot


def density_map(df):
    van_base = (
        alt.Chart(data_geojson_remote)
        .mark_geoshape(fill="lightgray")
        .project(type="identity", reflectY=True)
    )

    plot_van = (
        van_base
        + alt.Chart(df)
        .transform_lookup(
            default="0",
            as_="geo",
            lookup="NEIGHBOURHOOD_NAME",
            from_=alt.LookupData(data=data_geojson_remote, key="properties.name"),
        )
        .mark_geoshape()
        .encode(
            alt.Color("count()", scale=alt.Scale(scheme="redpurple")),
            alt.Shape(field="geo", type="geojson"),
            tooltip=["count()", "NEIGHBOURHOOD_NAME:N"],
        )
    ).project(type="identity", reflectY=True)

    return plot_van.to_html()


def bar_plot(trees_bar):
    trees_bar = trees_bar.dropna(subset=["COMMON_NAME", "NEIGHBOURHOOD_NAME"])

    bar_plot = (
        alt.Chart(trees_bar)
        .mark_bar()
        .encode(
            x=alt.X("count:Q", axis=alt.Axis(title="Number of Trees")),
            y=alt.Y(
                "COMMON_NAME:N",
                axis=alt.Axis(title="Tree Name"),
                sort=alt.SortField("count", order="descending"),
            ),
            tooltip=alt.Tooltip("count:Q"),
        )
        .transform_aggregate(count="count()", groupby=["COMMON_NAME"])
        .transform_filter("datum.count >= 10")
        .configure_mark(opacity=0.6, color="pink")
        .interactive()
    )

    return bar_plot.to_html()


##Create Timeline Chart
def timeline_plot(trees_timeline):
    trees_timeline = trees_timeline.dropna(subset=["BLOOM_START", "BLOOM_END"])

    timeline = (
        alt.Chart(trees_timeline)
        .mark_bar()
        .encode(
            x=alt.X(
                "BLOOM_START",
                axis=alt.Axis(
                    values=[
                        d.isoformat()
                        for d in pd.date_range(
                            start="2022-01-01", end="2022-5-31", freq="1M"
                        )
                    ],
                    format="%b",
                    tickCount=5,
                    orient="top",
                ),
                title=None,
            ),
            x2="BLOOM_END",
            y=alt.Y("CULTIVAR_NAME:N", title=None),
            tooltip=[
                alt.Tooltip("BLOOM_START", title="Start"),
                alt.Tooltip("BLOOM_END", title="End"),
            ],
        )
        .configure_mark(color="pink")
        .configure_axis(domainOpacity=0)
        .configure_view(strokeOpacity=0)
    )

    return timeline.to_html()


@app.callback(
    Output("bar", "srcDoc"),
    Output("timeline", "srcDoc"),
    Output("density", "srcDoc"),
    Output("map", "figure"),
    Input("picker_date", "start_date"),
    Input("picker_date", "end_date"),
    Input("filter_neighbourhood", "value"),
    Input("filter_cultivar", "value"),
    Input("slider_diameter", "value"),
)
def main_callback(start_date, end_date, neighbourhood, cultivar, diameter_range):
    # Build new dataset and call all charts

    # Date input Cleanup
    if start_date is None:
        start_date = "2022-01-01"
    if end_date is None:
        end_date = "2022-05-30"
    start_date = pd.Timestamp(date.fromisoformat(start_date))
    end_date = pd.Timestamp(date.fromisoformat(end_date))

    filtered_trees = raw_trees
    # Filter by neighbourhood
    if neighbourhood != "all_neighbourhoods":
        filtered_trees = filtered_trees[
            filtered_trees["NEIGHBOURHOOD_NAME"] == neighbourhood
        ]

    # Filter by date

    filtered_trees = filtered_trees[
        (
            (filtered_trees["BLOOM_START"] <= start_date)
            & (filtered_trees["BLOOM_END"] >= start_date)
        )
        | (
            (filtered_trees["BLOOM_START"] <= end_date)
            & (filtered_trees["BLOOM_END"] >= end_date)
        )
        | (filtered_trees["BLOOM_START"].between(start_date, end_date))
        | (filtered_trees["BLOOM_END"].between(start_date, end_date))
    ]

    # Filter by Diameter
    filtered_trees = filtered_trees[
        filtered_trees["DIAMETER"].between(diameter_range[0], diameter_range[1])
    ]

    if cultivar != "all_cultivars":
        filtered_trees = filtered_trees[filtered_trees["CULTIVAR_NAME"] == cultivar]

    bar = bar_plot(filtered_trees)
    timeline = timeline_plot(filtered_trees)
    density = density_map(filtered_trees)
    big_map = street_map(filtered_trees)

    return bar, timeline, density, big_map


if __name__ == "__main__":
    app.run_server(debug=True)
