
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# -----------------------------------
# 1. Page Configuration
# -----------------------------------

st.set_page_config(
    page_title="BMTC Transport Analytics",
    page_icon="🚌",
    layout="wide"
)

st.title("🚌 Bengaluru BMTC Route & Schedule Analysis")
st.markdown(
    "An interactive dashboard to explore BMTC scheduled services, "
    "busy stops, routes and stop clusters."
)

st.info(
    "This dashboard uses GTFS scheduled transport data. "
    "It analyses scheduled services, not actual bus delays or live arrivals."
)

# -----------------------------------
# 2. Load Dataset
# -----------------------------------

DATA_DIR = Path(".")

@st.cache_data
def load_data():
    stops = pd.read_csv(DATA_DIR / "clustered_stops.csv")
    routes = pd.read_csv(DATA_DIR / "top_routes.csv")
    return stops, routes

try:
    stops, routes = load_data()
except FileNotFoundError:
    st.error(
        "CSV files not found. Please add clustered_stops.csv "
        "and top_routes.csv inside the dashboard_exports folder."
    )
    st.stop()

# -----------------------------------
# 3. Identify Columns
# -----------------------------------

def find_column(data, possible_names):
    for name in possible_names:
        for column in data.columns:
            if column.lower() == name.lower():
                return column
    return None

stop_name_col = find_column(
    stops, ["stop_name", "stop_name_x", "name"]
)

stop_id_col = find_column(
    stops, ["stop_id", "id"]
)

trips_col = find_column(
    stops,
    ["scheduled_trips_count", "scheduled_trips",
     "trip_count", "trips"]
)

routes_count_col = find_column(
    stops,
    ["unique_routes_count", "unique_routes",
     "route_count", "routes_count"]
)

cluster_col = find_column(
    stops, ["cluster_k2", "cluster", "cluster_label"]
)

lat_col = find_column(
    stops, ["stop_lat", "latitude", "lat"]
)

lon_col = find_column(
    stops, ["stop_lon", "longitude", "lon", "lng"]
)

route_name_col = find_column(
    routes,
    ["route_short_name", "route_long_name", "route_id", "route_name", "route"]
)

route_trips_col = find_column(
    routes,
    ["total_trips", "trip_count", "scheduled_trips", "trips", "unique_trips"]
)

if trips_col is None or stop_name_col is None:
    st.error(
        "Required columns were not found in clustered_stops.csv. "
        "Please check the CSV column names."
    )
    st.write("Available columns:", list(stops.columns))
    st.stop()

# -----------------------------------
# 4. Sidebar Filters
# -----------------------------------

st.sidebar.header("Dashboard Filters")

filtered_stops = stops.copy()

if cluster_col:
    clusters = sorted(
        filtered_stops[cluster_col].dropna().unique(),
        key=lambda value: str(value)
    )

    selected_clusters = st.sidebar.multiselect(
        "Select Stop Cluster",
        clusters,
        default=clusters
    )

    filtered_stops = filtered_stops[
        filtered_stops[cluster_col].isin(selected_clusters)
    ]

# -----------------------------------
# 5. KPI Metrics
# -----------------------------------

st.subheader("📊 Dashboard Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Stops", f"{len(filtered_stops):,}")
col2.metric(
    "Total Scheduled Trips",
    f"{filtered_stops[trips_col].sum():,.0f}"
)

if routes_count_col:
    col3.metric(
        "Average Routes per Stop",
        f"{filtered_stops[routes_count_col].mean():.1f}"
    )
else:
    col3.metric("Route Data", "Available in route section")

col4.metric("Routes in Export", f"{len(routes):,}")

st.divider()

# -----------------------------------
# 6. Stop Analysis
# -----------------------------------

st.subheader("🚏 Stop Analysis")

top_stops = filtered_stops.sort_values(
    trips_col, ascending=False
).head(15)

fig_stops = px.bar(
    top_stops,
    x=trips_col,
    y=stop_name_col,
    orientation="h",
    title="Top 15 Stops by Scheduled Trips",
    labels={
        trips_col: "Scheduled Trips",
        stop_name_col: "Stop Name"
    },
    hover_data=[stop_id_col] if stop_id_col else None
)

fig_stops.update_layout(
    yaxis={"categoryorder": "total ascending"}
)

st.plotly_chart(fig_stops, use_container_width=True)

# -----------------------------------
# 7. Route Analysis
# -----------------------------------

st.subheader("🛣️ Route Analysis")

if route_name_col and route_trips_col:
    top_routes = routes.sort_values(
        route_trips_col, ascending=False
    ).head(15)

    fig_routes = px.bar(
        top_routes,
        x=route_name_col,
        y=route_trips_col,
        title="Top Routes by Scheduled Trips",
        labels={
            route_name_col: "Route",
            route_trips_col: "Scheduled Trips"
        }
    )

    st.plotly_chart(fig_routes, use_container_width=True)

else:
    st.warning(
        "Could not identify the route name and trip count columns. "
        "Available columns:"
    )
    st.write(list(routes.columns))

# -----------------------------------
# 8. Stop Clustering
# -----------------------------------

st.subheader("🤖 K-Means Stop Clustering")

if cluster_col:
    cluster_summary = filtered_stops.groupby(
        cluster_col
    ).agg(
        Number_of_Stops=(stop_name_col, "count"),
        Average_Scheduled_Trips=(trips_col, "mean")
    ).reset_index()

    cluster_summary["Average_Scheduled_Trips"] = (
        cluster_summary["Average_Scheduled_Trips"].round(2)
    )

    st.dataframe(
        cluster_summary,
        use_container_width=True,
        hide_index=True
    )

    fig_cluster = px.pie(
        cluster_summary,
        names=cluster_col,
        values="Number_of_Stops",
        title="Distribution of Stops Across Clusters"
    )

    st.plotly_chart(fig_cluster, use_container_width=True)

else:
    st.warning("Cluster column not found in the stop dataset.")

# -----------------------------------
# 9. Bengaluru Stop Map
# -----------------------------------

st.subheader("📍 Geographic Distribution of Stops")

if lat_col and lon_col:
    map_data = filtered_stops[
        [lat_col, lon_col]
    ].copy()

    map_data[lat_col] = pd.to_numeric(
        map_data[lat_col], errors="coerce"
    )

    map_data[lon_col] = pd.to_numeric(
        map_data[lon_col], errors="coerce"
    )

    map_data = map_data.dropna()

    st.map(
        map_data.rename(
            columns={lat_col: "latitude", lon_col: "longitude"}
        )
    )
else:
    st.warning(
        "Latitude and longitude columns were not found. "
        "The stop map cannot be displayed."
    )

# -----------------------------------
# 10. Detailed Stop Table
# -----------------------------------

st.subheader("📋 Stop Details")

search = st.text_input("Search for a stop")

if search:
    display_stops = filtered_stops[
        filtered_stops[stop_name_col].astype(str).str.contains(
            search, case=False, na=False
        )
    ]
else:
    display_stops = filtered_stops

st.dataframe(
    display_stops,
    use_container_width=True,
    hide_index=True
)

# -----------------------------------
# 11. Download Filtered Data
# -----------------------------------

csv_data = display_stops.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Stop Data",
    data=csv_data,
    file_name="bmtc_stop_analysis.csv",
    mime="text/csv"
)

# -----------------------------------
# 12. Footer
# -----------------------------------

st.divider()

st.caption(
    "Project: Bengaluru BMTC Route & Schedule Analysis | "
    "Data source: GTFS schedule snapshot, 7–13 November 2024"
)
