import networkx as nx
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import warnings
import geopandas as gpd
import momepy
import contextily as ctx
import folium

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

def draw_graph(G, affected_nodes=set(), removed_edges=set()):
    fig, ax = plt.subplots(figsize=(20, 20), dpi = 500)  # Adjust the canvas size
    gdf = gpd.GeoDataFrame(df1, geometry=gpd.points_from_xy(df1.Longitude, df1.Latitude))
    gdf.crs = 'EPSG:4326'
    
    pos = nx.get_node_attributes(G, 'pos')


    
    nx.draw(G, pos, with_labels=False, width=2, edge_color='#474747', node_color='#FFC125', node_size=200)
    
    # Draw removed edges as broken lines
    for edge in removed_edges:
        source, target = edge
        if source in pos and target in pos:
            xs, ys = pos[source]
            xt, yt = pos[target]
            plt.plot([xs, xt], [ys, yt], color='red', linewidth=2, linestyle='dashed')
    
    nx.draw_networkx_nodes(G, pos, nodelist=affected_nodes, node_color='red', node_size=500)
    
    # Draw affected edges in red
    affected_edges_list = affected_edges(G, affected_nodes)
    nx.draw_networkx_edges(G, pos, edgelist=affected_edges_list, edge_color='red', width=2)
    
    # Adjust label positions
    label_pos = {k: (v[0], v[1] + 0.01) for k, v in pos.items()}
    nx.draw_networkx_labels(G, label_pos, font_size=10, font_family='sans-serif', font_color="black", font_weight="bold")
    
    plt.axis('off')
    ctx.add_basemap(ax, crs=gdf.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)

    return plt

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
    st.pyplot(plt)

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
    st.pyplot(plt)

