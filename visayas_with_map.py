import networkx as nx
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import warnings
import geopandas as gpd
import momepy
import contextily as ctx
import folium
from streamlit_folium import folium_static


edges = [('Ormoc','Babatngon'), ('Babatngon', 'Sta Rita Tap'),('Babatngon','Paranas'),('Sta Rita Tap', 'Sta. Rita'),('Sta Rita Tap','Paranas'),('Paranas','Sta Rita Tap'),('Paranas','Calbayog'),\
                  ('Ormoc','Isabel'),('Ormoc','Maasin'),('Ormoc','Tongonan'),('Kananga','Ormoc'),('Tabango','Kananga'),\
                 ('Maasin','Ubay'),('Ubay','Corella'),('Daan Bantayan','Tabango'),('Compostela','Daan Bantayan'),('Cebu','Compostela'),('Cebu','Mandaue'),('Lapu-Lapu','Mandaue')\
                  ,('Quiot','Cebu'),('Colon','Cebu'),('Naga','Colon',),('Samboan','Colon'),('Magdugo','Colon'),('Therma Visayas','Magdugo')\
                  ,('KSPC','Colon'),('Toledo','Colon'),('Calung-Calung','Colon'),('DaangLungsod','Calung-Calung'),('Calung-Calung','Colon'),('DaangLungsod','Magdugo')\
                  ,('Colon','Quiot'),('PGPP1', 'Amlan'), ('PGPP2', 'Amlan'), ('Mabinay','Amlan')\
                  ,('Kabankalan','Mabinay'), ('Kabankalan Bess', 'Kabankalan'), ('Bacolod','Kabankalan'), ('Helios', 'Cadiz'), ('Cadiz','Bacolod')\
                  ,('Helios', 'Bacolod'),('Amlan','Samboan'),('Bacolod', 'Barotac Viejo'),('Barotac Viejo','Bacolod'),('Concepcion','Barotac Viejo'), ('Barotac Viejo', 'Dingle'),('Dingle','Barotac Viejo')\
                  ,('Panit-an','Dingle'), ('Dingle', 'Sta. Barbara S/S'),('Sta. Barbara S/S','Dingle'),('Nabas', 'Panit-an'), ('San Jose', 'Sta. Barbara S/S'), ('Iloilo 1', 'Sta. Barbara S/S')\
                  ,('Buenavista', 'Sta. Barbara S/S')]


df1 = pd.read_csv("coord1.csv")
### call data source for customer list
affected_customers=pd.read_excel('cc_du_2.xlsx')

def create_sample_graph():
    gdf = gpd.GeoDataFrame(df1, geometry=gpd.points_from_xy(df1.Longitude, df1.Latitude))
    gdf.crs = 'EPSG:4326'
    
    G = nx.DiGraph()
    
    for index, row in gdf.iterrows():
        G.add_node(row['Substation'], pos=(row['geometry'].x, row['geometry'].y))
    
    for edge in edges:
        G.add_edge(edge[0], edge[1])

    return G

def affected_nodes(G, edges_to_remove):
    affected = set()
    for edge in edges_to_remove:
        source, target = edge
        for node in nx.dfs_preorder_nodes(G, source=target):
            affected.add(node)
    return affected

def affected_edges(G, affected_nodes):
    affected_edges = set()
    for node in affected_nodes:
        for edge in G.edges(node):
            affected_edges.add(edge)
    return affected_edges

def draw_graph_folium(G, affected_nodes=set(), removed_edges=set()):
    gdf = gpd.GeoDataFrame(df1, geometry=gpd.points_from_xy(df1.Longitude, df1.Latitude))
    gdf.crs = 'EPSG:4326'
    gdf = gdf.to_crs(epsg=3857)

    pos = {node: (gdf.loc[gdf['Substation'] == node, 'geometry'].values[0].x, gdf.loc[gdf['Substation'] == node, 'geometry'].values[0].y) for node in G.nodes}

    m = folium.Map(location=[10.3157, 123.8854], zoom_start=8, tiles='cartodb positron')

    for node, coords in pos.items():
        if node in affected_nodes:
            folium.CircleMarker(location=[coords[1], coords[0]], radius=5, color='red', fill=True, fill_color='red').add_to(m)
        else:
            folium.CircleMarker(location=[coords[1], coords[0]], radius=3, color='blue', fill=True, fill_color='blue').add_to(m)
        folium.Popup(node).add_to(m)

    for edge in G.edges:
        source, target = edge
        if source in pos and target in pos:
            xs, ys = pos[source]
            xt, yt = pos[target]
            if edge in removed_edges:
                folium.PolyLine([(ys, xs), (yt, xt)], color='red', weight=2, opacity=1).add_to(m)
            else:
                folium.PolyLine([(ys, xs), (yt, xt)], color='blue', weight=1, opacity=0.5).add_to(m)

    return m


st.title("Electricity Grid Network Analysis")

G = create_sample_graph()

st.write("Visayas Lines:")
st.write(G.edges)


edges_to_remove = st.multiselect("Select Line Trippings:", list(G.edges))


if st.button("Line Tripped"):
    for edge in edges_to_remove:
        G.remove_edge(*edge)
    st.write(f"Edges {edges_to_remove} removed.")
    st.write("Updated graph:")
    st.write(G.edges)

    affected = affected_nodes(G, edges_to_remove)
    st.write("Affected Areas:")
    st.write(affected)
    #---------- affected customer & demand

    # filter affected customers
    filtered_df = affected_customers[affected_customers['node'].isin(affected)] 

    #-- DUs
    # filter affected DUs
    affected_DUs = filtered_df[filtered_df['type']=='DU']
    affected_DUs= affected_DUs[['Name','Short Name']].reset_index(drop=True)
    
    #get MW of affected DUs
    affected_du_MW= filtered_df[filtered_df['type']=='DU'].drop_duplicates(subset=['Name'])
    affected_du_MW_value=affected_du_MW['Estimated Demand (MW)'].sum()   #sum of affected DU MWs (captive)
    
    #-- CCs
    # filter affected CCs
    affected_CCs = filtered_df[filtered_df['type']=='CC']  #['customer_name','node']
    affected_CCs= affected_CCs[['Name','node']].reset_index(drop=True)

    #get MW of affected CCs
    affected_cc_MW= filtered_df[filtered_df['type']=='CC'].drop_duplicates(subset=['Name','node'])
    affected_cc_MW_value=affected_cc_MW['Estimated Demand (MW)'].sum()

    st.write("Visayas Electricity Grid:")
    plt = draw_graph(G, affected, edges_to_remove)
    m = draw_graph_folium(G, affected, edges_to_remove)
    folium_static(m)

    #-- write output
    
    st.write("Estimated Affected Demand: " + str(affected_du_MW_value+affected_du_MW_value) + " MW")
    
    st.write("Affected DUs:")
    st.write(affected_DUs)

    st.write("Affected Contestable Customers")
    st.write(affected_CCs)

    


    #----------end of affected customer & demand
else:
    st.write("Visayas Electricity Grid:")
    plt = draw_graph(G)
    m = draw_graph_folium(G)
    folium_static(m)

