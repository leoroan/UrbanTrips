import numpy as np
import geopandas as gpd
import folium
import pandas as pd
from urbantrips.geo import geo
from urbantrips.kpi import overlapping as ovl
from urbantrips.utils.utils import leer_configs_generales, iniciar_conexion_db


def get_route_metadata(route_id):
    configs = leer_configs_generales()
    conn_insumos = iniciar_conexion_db(tipo="insumos")
    use_branches = configs["lineas_contienen_ramales"]
    if use_branches:
        metadata = pd.read_sql(
            f"select nombre_ramal from metadata_ramales where id_ramal  == {route_id}",
            conn_insumos,
        )
        metadata = metadata.nombre_ramal.iloc[0]
    else:
        metadata = pd.read_sql(
            f"select nombre_linea from metadata_lineas where id_linea  == {route_id}",
            conn_insumos,
        )
        metadata = metadata.nombre_linea.iloc[0]
    return metadata


def plot_interactive_supply_overlapping(overlapping_dict):

    base_route_id = overlapping_dict["base"]["h3"].route_id.unique()[0]
    comp_route_id = overlapping_dict["comp"]["h3"].route_id.unique()[0]
    base_route_metadata = get_route_metadata(base_route_id)
    comp_route_metadata = get_route_metadata(comp_route_id)

    # extract data from overlapping dict
    base_gdf = overlapping_dict["base"]["h3"]
    base_route_gdf = overlapping_dict["base"]["line"]
    comp_gdf = overlapping_dict["comp"]["h3"]
    comp_route_gdf = overlapping_dict["comp"]["line"]

    # get mean coords to center map
    mean_x = np.mean(base_route_gdf.item().coords.xy[0])
    mean_y = np.mean(base_route_gdf.item().coords.xy[1])

    fig = folium.Figure(width=1000, height=600)
    m = folium.Map(location=(mean_y, mean_x), zoom_start=11, tiles="cartodbpositron")

    base_gdf.explore(
        color="black",
        tiles="CartoDB positron",
        m=m,
        name=f"Base H3 {base_route_metadata}",
    )
    base_route_gdf.explore(
        color="black",
        tiles="CartoDB positron",
        m=m,
        name=f"Base route {base_route_metadata}",
    )

    comp_gdf.explore(
        color="red",
        tiles="CartoDB positron",
        m=m,
        name=f"Comp H3 {comp_route_metadata}",
    )
    comp_route_gdf.explore(
        color="red",
        tiles="CartoDB positron",
        m=m,
        name=f"Comp route {comp_route_metadata}",
    )

    folium.LayerControl(name="Legs").add_to(m)

    fig.add_child(m)
    return fig


def plot_interactive_demand_overlapping(base_demand, comp_demand, overlapping_dict):
    base_gdf = overlapping_dict["base"]["h3"]
    base_route_gdf = overlapping_dict["base"]["line"]
    comp_gdf = overlapping_dict["comp"]["h3"]
    comp_route_gdf = overlapping_dict["comp"]["line"]

    base_route_id = base_gdf.route_id.unique()[0]
    comp_route_id = comp_gdf.route_id.unique()[0]

    base_route_metadata = get_route_metadata(base_route_id)
    comp_route_metadata = get_route_metadata(comp_route_id)

    # Points for O and D
    base_origins = (
        base_demand.reindex(columns=["h3_o", "factor_expansion_linea"])
        .groupby("h3_o", as_index=False)
        .agg(total_legs=("factor_expansion_linea", "sum"))
    )
    base_destinations = (
        base_demand.reindex(columns=["h3_d", "factor_expansion_linea"])
        .groupby("h3_d", as_index=False)
        .agg(total_legs=("factor_expansion_linea", "sum"))
    )
    base_origins = gpd.GeoDataFrame(
        base_origins, geometry=base_origins.h3_o.map(geo.create_point_from_h3), crs=4326
    )
    base_destinations = gpd.GeoDataFrame(
        base_destinations,
        geometry=base_destinations.h3_d.map(geo.create_point_from_h3),
        crs=4326,
    )

    comp_origins = (
        comp_demand.reindex(columns=["h3_o", "factor_expansion_linea"])
        .groupby("h3_o", as_index=False)
        .agg(total_legs=("factor_expansion_linea", "sum"))
    )
    comp_destinations = (
        comp_demand.reindex(columns=["h3_d", "factor_expansion_linea"])
        .groupby("h3_d", as_index=False)
        .agg(total_legs=("factor_expansion_linea", "sum"))
    )
    comp_origins = gpd.GeoDataFrame(
        comp_origins, geometry=comp_origins.h3_o.map(geo.create_point_from_h3), crs=4326
    )
    comp_destinations = gpd.GeoDataFrame(
        comp_destinations,
        geometry=comp_destinations.h3_d.map(geo.create_point_from_h3),
        crs=4326,
    )

    # compute demand by section id
    base_demand_by_section = ovl.demand_by_section_id(base_demand)
    comp_demand_by_section = ovl.demand_by_section_id(comp_demand)

    # plot
    base_gdf = base_gdf.merge(base_demand_by_section, on="section_id", how="left")
    base_gdf.total_legs = base_gdf.total_legs.fillna(0)
    base_gdf.prop_demand = base_gdf.prop_demand.fillna(0)

    comp_gdf = comp_gdf.merge(comp_demand_by_section, on="section_id", how="left")
    comp_gdf.total_legs = comp_gdf.total_legs.fillna(0)
    comp_gdf.prop_demand = comp_gdf.prop_demand.fillna(0)

    min_dot_size = 1
    max_dot_size = 20

    base_destinations["total_legs_normalized"] = ovl.normalize_total_legs_to_dot_size(
        base_destinations["total_legs"], min_dot_size, max_dot_size
    )
    comp_destinations["total_legs_normalized"] = ovl.normalize_total_legs_to_dot_size(
        comp_destinations["total_legs"], min_dot_size, max_dot_size
    )
    base_origins["total_legs_normalized"] = ovl.normalize_total_legs_to_dot_size(
        base_origins["total_legs"], min_dot_size, max_dot_size
    )
    comp_origins["total_legs_normalized"] = ovl.normalize_total_legs_to_dot_size(
        comp_origins["total_legs"], min_dot_size, max_dot_size
    )

    fig = folium.Figure(width=1000, height=600)
    m = folium.Map(location=(-34.606, -58.436), zoom_start=11, tiles="cartodbpositron")

    base_gdf.explore(
        column="total_legs",
        tiles="CartoDB positron",
        m=m,
        name=f"Demanda ruta base - {base_route_metadata}",
        cmap="Blues",
        scheme="equalinterval",
    )
    base_destinations.explore(
        color="midnightblue",
        style_kwds={
            "style_function": lambda x: {
                "radius": x["properties"]["total_legs_normalized"]
            }
        },
        name=f"Destinos ruta base - {base_route_metadata}",
        m=m,
    )
    base_origins.explore(
        color="cornflowerblue",
        style_kwds={
            "style_function": lambda x: {
                "radius": x["properties"]["total_legs_normalized"]
            }
        },
        name=f"Origenes ruta base - {base_route_metadata}",
        m=m,
    )
    base_route_gdf.explore(
        color="midnightblue",
        tiles="CartoDB positron",
        m=m,
        name=f"Ruta base - {comp_route_metadata}",
    )

    comp_gdf.explore(
        column="total_legs",
        tiles="CartoDB positron",
        m=m,
        name=f"Demanda ruta comp - {comp_route_metadata}",
        cmap="Greens",
        scheme="equalinterval",
    )
    comp_destinations.explore(
        color="darkgreen",
        style_kwds={
            "style_function": lambda x: {
                "radius": x["properties"]["total_legs_normalized"]
            }
        },
        name=f"Destinos ruta comp - {comp_route_metadata}",
        m=m,
    )
    comp_origins.explore(
        color="limegreen",
        style_kwds={
            "style_function": lambda x: {
                "radius": x["properties"]["total_legs_normalized"]
            }
        },
        name=f"Origenes ruta comp - {comp_route_metadata}",
        m=m,
    )
    comp_route_gdf.explore(
        color="darkgreen",
        tiles="CartoDB positron",
        m=m,
        name=f"Ruta comparacion - {comp_route_metadata}",
    )

    folium.LayerControl(name="Leyenda").add_to(m)

    fig.add_child(m)
    return fig