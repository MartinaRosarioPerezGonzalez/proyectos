import pandas as pd
import networkx as nx
import os
from pathlib import Path
from src import (
    clean_dataframe,
    get_basic_metrics,
    get_connected_components,
    calculate_all_centralities, 
    compute_communities,
    create_subgraph_by_metric,
    create_subgraph_by_in_degree,
    create_subgraph_by_degree,
    plot_top_metrics, 
    plot_wordcloud_and_rank,
    plot_communities_distribution,
    export_to_gephi
)

# ============================================================
# CONFIGURATION
# ============================================================

CONFIG = {
    "output_dirs": ["output", "output/images", "output/gephi", "output/csv"],
    "load_params": {
        "load_centralities" : True
    },
    "subgraph_params": {
        "in_degree_threshold": 500,
        "degree_min": 45,
        "pagerank_percentile": 0.95,
        "betweenness_top_n": 300,
        "communities_top_n": 4
    },
    "visualization_params": {
        "top_n_metrics": 15,
        "pagerank_max_iter": 50
    }
}

def setup_directories():
    """Create output directories."""
    for directory in CONFIG["output_dirs"]:
        os.makedirs(directory, exist_ok=True)

def load_and_clean_data(file_path, year):
    """Load and clean data from CSV or Parquet."""
    file_path = Path(file_path)
    print(f"\n📂 Loading {file_path.name} for year {year}...")
    
    try:
        if file_path.suffix == ".parquet":
            df = clean_dataframe(str(file_path))
        elif file_path.suffix == ".csv":
            df = pd.read_csv(file_path)
        else:
            raise ValueError(f"Unsupported format: {file_path.suffix}")
        
        # Ensure correct columns exist
        if 'package_name' not in df.columns or 'requirement' not in df.columns:
            print(f"⚠ CSV columns: {df.columns.tolist()}")
            print(f"⚠ Expected: package_name, requirement")
            raise ValueError("Missing required columns")
        
        # Keep only necessary columns
        df = df[['package_name', 'requirement']]
        
        # Remove NaNs
        df = df.dropna()
        
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Save clean data
        if file_path.suffix == ".parquet":
            os.makedirs("data", exist_ok=True) # Ensure dir exists
            out_path = f"data/clean_data_{year}.csv"
            df.to_csv(out_path, index=False)
            print(f"✓ Saved clean dataframe to {out_path}")
        
        print(f"✓ Loaded: {len(df):,} clean rows ({df['package_name'].nunique():,} packages)")
        return df
    except Exception as e:
        print(f"✗ Error loading {file_path}: {e}")
        return None

def load_descriptions():
    """Load descriptions for wordclouds."""
    try:
        df = pd.read_parquet("data/raw.parquet")
        df['name_clean'] = df['name'].str.lower().str.strip()
        return df
    except:
        return None

def analyze_single_dataset(year, df_clean, df_descriptions):
    """Analyze a single year dataset."""
    print(f"\n{'='*60}\n ANALYZING YEAR: {year}\n{'='*60}")
    
    # Build graph
    G = nx.from_pandas_edgelist(
        df_clean, source='package_name', target='requirement', create_using=nx.DiGraph()
    )
    G_und = G.to_undirected()
    print(f"✓ Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # Metrics
    print("\n--- BASIC METRICS ---")
    stats = get_basic_metrics(G)
    for k, v in stats.items():
        print(f"{k}: {v:,.2f}" if isinstance(v, float) else f"{k}: {v:,}")
    
    # Components
    print("\n--- CONNECTED COMPONENTS ---")
    comp_stats = get_connected_components(G)
    for k, v in comp_stats.items():
        print(f"{k}: {v}")
    
    # Centralities
    if CONFIG["load_params"]["load_centralities"]:
        print("\n--- LOADING CENTRALITIES ---")
        file_path = f"./output/csv/centralities_{year}.csv"
        try:
            df_metrics = pd.read_csv(file_path)
            print("✓ Loaded")
        except Exception as e:
            print(f"✗ Error loading {file_path}: {e}")
            print("\n--- CALCULATING CENTRALITIES ---")
            df_metrics = calculate_all_centralities(G)
            print("✓ Calculated")
        
    else:
        print("\n--- CALCULATING CENTRALITIES ---")
        df_metrics = calculate_all_centralities(G)
        print("✓ Calculated")
    
    # Visualize Metrics
    print("\n--- VISUALIZING METRICS ---")
    for col in [
        "degree_centrality", "pagerank", "betweenness_centrality", "closeness_centrality"
        ]:
        plot_top_metrics(df_metrics, col, year, top_n=CONFIG["visualization_params"]["top_n_metrics"])
    
    # Communities
    print("\n--- COMMUNITIES ---")
    G_und, partition, modularity, comm_sizes = compute_communities(G_und)
    print(f"✓ Found {len(set(partition.values()))} communities")
    print(f"✓ Modularity: {modularity:.4f}")

    print("\n--- VISUALIZING COMMUNITY DISTRIBUTION ---")    
    plot_communities_distribution(comm_sizes, year, 15)
    
    # Subgraphs
    print("\n--- SUBGRAPHS ---")
    pr_dict = dict(zip(df_metrics['node'], df_metrics['pagerank']))
    bet_dict = dict(zip(df_metrics['node'], df_metrics['betweenness_centrality']))
    
    try:
        sub_deg, _ = create_subgraph_by_in_degree(G, threshold=CONFIG["subgraph_params"]["in_degree_threshold"])
        print(f"✓ In-degree: {sub_deg.number_of_nodes()} nodes")
        export_to_gephi(sub_deg, f"output/gephi/subgrafo_in_degree_{year}.gexf")
    except Exception as e:
        print(f"⚠ In-degree error: {e}")
    
    try:
        sub_deg, _ = create_subgraph_by_degree(G_und, min_degree=CONFIG["subgraph_params"]["degree_min"])
        print(f"✓ Degree: {sub_deg.number_of_nodes()} nodes")
        export_to_gephi(sub_deg, f"output/gephi/subgrafo_degree_{year}.gexf")
    except Exception as e:
        print(f"⚠ Degree error: {e}")
    
    try:
        pr_series = pd.Series(pr_dict)
        threshold = pr_series.quantile(CONFIG["subgraph_params"]["pagerank_percentile"])
        nodes = [n for n, v in pr_dict.items() if v >= threshold]
        sub_pr = G.subgraph(nodes).copy()
        print(f"✓ PageRank: {sub_pr.number_of_nodes()} nodes")
        export_to_gephi(sub_pr, f"output/gephi/subgrafo_pagerank_{year}.gexf")
    except Exception as e:
        print(f"⚠ PageRank error: {e}")
    
    try:
        top_n = CONFIG["subgraph_params"]["betweenness_top_n"]
        sub_bet, _ = create_subgraph_by_metric(G, bet_dict, top_n=top_n)
        print(f"✓ Betweenness (top {top_n}): {sub_bet.number_of_nodes()} nodes")
        export_to_gephi(sub_bet, f"output/gephi/subgrafo_betweenness_{year}.gexf")
    except Exception as e:
        print(f"⚠ Betweenness error: {e}")
    
    # Export
    print("\n--- EXPORTING CSV ---")
    df_metrics.to_csv(f"output/csv/centralities_{year}.csv", index=False)
    pd.DataFrame({
        'community_id': comm_sizes.index,
        'size': comm_sizes.values,
        'percentage': 100 * comm_sizes.values / len(partition)
    }).to_csv(f"output/csv/communities_{year}.csv", index=False)
    pd.DataFrame({
        'Metric': list(stats.keys()) + list(comp_stats.keys()),
        'Value': list(stats.values()) + list(comp_stats.values())
    }).to_csv(f"output/csv/summary_{year}.csv", index=False)
    print("✓ Exported")
    
    # Wordclouds
    if df_descriptions is not None:
        print("\n--- WORDCLOUDS ---")
        try:
            for i, comm_id in enumerate(comm_sizes.head(CONFIG["subgraph_params"]["communities_top_n"]).index, 1):
                nodes_comm = [n for n, c in partition.items() if c == comm_id]
                plot_wordcloud_and_rank(
                    nodes_comm, f"Year {year} - Community Top {i}", f"{year}_{i}",
                    pr_dict, df_descriptions,
                    save=True, save_path=f"output/images/wordcloud_{year}_{i}.png"
                )
            print("✓ Generated")
        except Exception as e:
            print(f"⚠ Error: {e}")
    
    return stats

# ============================================================
# MAIN: ANALYZE DATASETS
# ============================================================

def analyze_datasets(**datasets):
    """
    Analyze one or multiple datasets.
    Pass datasets as keyword arguments: year_key=file_path
    
    Example:
        analyze_datasets(Y2016="data/clean_data_2016.csv")
        analyze_datasets(Y2016="data/raw_2016.parquet", Y2025="data/clean_data_2025.csv")
        analyze_datasets(Y2025="data/raw.parquet")
    """
    if not datasets:
        print("❌ No datasets provided!")
        return
    
    setup_directories()
    df_desc = load_descriptions()
    
    results = {}
    
    # Process datasets
    for year_key, file_path in datasets.items():
        year = year_key.replace("Y", "")
        df = load_and_clean_data(file_path, year)
        if df is not None:
            stats = analyze_single_dataset(year, df, df_desc)
            results[year] = stats
    
    # Compare if multiple datasets
    if len(results) > 1:
        print("\n" + "="*60)
        print(" COMPARISON TABLE")
        print("="*60)
        comparison_df = pd.DataFrame(results).T
        print(comparison_df)
        comparison_df.to_csv("output/csv/comparison.csv")
    
    print("\n✓ Complete!")

if __name__ == "__main__":
    # Example usage - uncomment and modify as needed:
    analyze_datasets(
        Y2016="data/clean_data_2016.csv",
        Y2025="data/raw.parquet"
    )
    
    # Or single dataset:
    # analyze_datasets(Y2025="data/raw.parquet")
    
    # Or mix CSV and parquet:
    # analyze_datasets(Y2016="data/raw_2016.parquet", Y2025="data/clean_data_2025.csv")