import pandas as pd
import networkx as nx
import community.community_louvain as community_louvain

def get_basic_metrics(G):
    """Returns a dictionary with basic graph statistics."""
    metrics = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "degree_avg": sum(dict(G.degree()).values()) / G.number_of_nodes()
    }
    
    if G.is_directed():
        metrics["in_degree_avg"] = sum(dict(G.in_degree()).values()) / G.number_of_nodes()
        metrics["out_degree_avg"] = sum(dict(G.out_degree()).values()) / G.number_of_nodes()
    
    return metrics

def get_connected_components(G):
    """Calculates strongly and weakly connected components for directed graphs."""
    if G.is_directed():
        scc = list(nx.strongly_connected_components(G))
        wcc = list(nx.weakly_connected_components(G))
        
        sizes_scc = [len(c) for c in scc]
        sizes_wcc = [len(c) for c in wcc]
        
        return {
            "strongly_connected": len(scc),
            "weakly_connected": len(wcc),
            "scc_max": max(sizes_scc) if sizes_scc else 0,
            "scc_min": min(sizes_scc) if sizes_scc else 0,
            "wcc_max": max(sizes_wcc) if sizes_wcc else 0,
            "wcc_min": min(sizes_wcc) if sizes_wcc else 0
        }
    else:
        cc = list(nx.connected_components(G))
        sizes = [len(c) for c in cc]
        return {
            "connected_components": len(cc),
            "cc_max": max(sizes) if sizes else 0,
            "cc_min": min(sizes) if sizes else 0
        }

def calculate_all_centralities(G, k_bet=1500):
    """
    Calculates the 4 main centrality metrics and returns a consolidated DataFrame.
    """
    print("Calculating Degree Centrality...")
    deg = nx.degree_centrality(G)
    
    print("Calculating PageRank...")
    pr = nx.pagerank(G)
    
    print(f"Calculating Betweenness (approx. with k={500})...")
    bet = nx.betweenness_centrality(G, k=500, seed=42)
    
    print("Calculating Closeness Centrality...")
    # Note: Closeness is computationally expensive O(n^2)
    clo = nx.closeness_centrality(G)
    
    # Consolidate into a single DataFrame
    df = pd.DataFrame({
        'node': list(deg.keys()),
        'degree_centrality': list(deg.values()),
        'pagerank': list(pr.values()),
        'betweenness_centrality': list(bet.values()),
        'closeness_centrality': list(clo.values())
    })
    
    return df

def get_top_subgraph(G, metric_dict, top_n=300):
    """Extracts a subgraph based on the top N nodes of a given metric."""
    top_nodes = sorted(metric_dict, key=metric_dict.get, reverse=True)[:top_n]
    return G.subgraph(top_nodes).copy()

def compute_communities(G_undirected, resolution=1.0):
    """Computes Louvain communities and adds attributes to the graph."""
    partition = community_louvain.best_partition(G_undirected, resolution=resolution, random_state=42)
    
    # Calculate additional info
    modularity = community_louvain.modularity(partition, G_undirected)
    community_sizes = pd.Series(partition.values()).value_counts()
    
    # Add attributes to nodes for export
    nx.set_node_attributes(G_undirected, partition, 'community')
    
    return G_undirected, partition, modularity, community_sizes

def export_to_gephi(G, filename, extra_attrs=None):
    """Standardized exporter for GEXF files."""
    if extra_attrs:
        nx.set_node_attributes(G, extra_attrs)
    nx.write_gexf(G, filename)

def create_subgraph_by_metric(G, metric_dict, top_n=300):
    """Extracts a subgraph based on the top N nodes of a given metric."""
    top_nodes = sorted(metric_dict, key=metric_dict.get, reverse=True)[:top_n]
    return G.subgraph(top_nodes).copy(), top_nodes

def create_subgraph_by_in_degree(G, threshold=500):
    """Creates a subgraph with nodes having in_degree > threshold."""
    if not G.is_directed():
        raise ValueError("in_degree only works with directed graphs")
    
    in_deg_map = dict(G.in_degree())
    filtered_nodes = {n for n, d in in_deg_map.items() if d > threshold}
    return G.subgraph(filtered_nodes).copy(), filtered_nodes

def create_subgraph_by_degree(G_undirected, min_degree=45):
    """Creates a subgraph with nodes having degree >= min_degree."""
    filtered_nodes = [n for n in G_undirected.nodes() if G_undirected.degree(n) >= min_degree]
    return G_undirected.subgraph(filtered_nodes).copy(), filtered_nodes

def create_top_communities_subgraph(G_undirected, partition, top_n=3):
    """Extracts a subgraph from top N communities by size."""
    community_sizes = pd.Series(partition.values()).value_counts()
    top_communities = community_sizes.head(top_n).index.tolist()
    
    nodes_in_communities = [node for node, comm in partition.items() if comm in top_communities]
    return G_undirected.subgraph(nodes_in_communities).copy(), top_communities