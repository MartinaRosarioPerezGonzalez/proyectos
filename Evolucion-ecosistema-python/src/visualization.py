import matplotlib.pyplot as plt
import re
from collections import Counter
from wordcloud import WordCloud
import pandas as pd
import os

def plot_top_metrics(df_metrics, metric_column, year, top_n=10):
    """
    Generates a horizontal bar chart for the top N nodes of a specific metric,
    following the visual style of the reference image.
    """

    topk = df_metrics.sort_values(metric_column, ascending=True).tail(top_n)
    
    plt.figure(figsize=(3, 12))
    
    ax = topk.set_index("node")[metric_column].plot(kind="barh", color='teal', alpha=0.6)
    ax.set_ylabel('')
    ax.tick_params(axis='both', labelsize=28)
    for spine in ax.spines.values(): 
        spine.set_visible(False)
    
    
    output_dir = "output/images"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    save_filename = f"top_{top_n}_{metric_column}_{year}.png"
    savepath = os.path.join(output_dir, save_filename)
    
    plt.savefig(savepath, bbox_inches='tight')
    print(f"Graph saved in: {savepath}")
    
    plt.show()
    
def plot_wordcloud_and_rank(nodes, title, i, pagerank_dict, df_descriptions, save=False, save_path=None):
    """Generates a combined WordCloud and PageRank bar chart for a community."""
    
    # Filter descriptions for nodes in this community
    descriptions = df_descriptions[df_descriptions['name'].isin(nodes)]['summary']
    
    all_words = []
    for d in descriptions:
        if d is None or pd.isna(d): 
            continue
        words = re.split(r"[ ,.-:(){\n}]+", str(d).lower())
        all_words += list(filter(None, words))

    counts = Counter(all_words)
    stop_words = {
        'for', 'a', 'library', 'and', 'the', 'package', 'python', 'in', 'to', 
        'with', 'of', 'as', 'is', 'it', 'on', 'an', 'that', '-', 'your', 
        'which', 'you', 'by', 'into', 'or', 'from', 'module', 'this', 'simple', 'fast'
    }

    count_filtered = {k: v for k, v in counts.items() if k not in stop_words}
    
    # Get top 10 nodes by PageRank for the side bar chart
    top_nodes = sorted(nodes, key=lambda n: pagerank_dict.get(n, 0), reverse=True)[:10]
    top_values = [pagerank_dict.get(n, 0) for n in top_nodes]

    # Create WordCloud
    wordcloud = WordCloud(
        width=600, height=800,
        background_color='white',
        colormap="tab10",
        random_state=42
    ).generate_from_frequencies(count_filtered)

    # Plotting
    fig, ax = plt.subplots(1, 2, figsize=(6.2, 3), gridspec_kw={'width_ratios': [2, 1]})
    
    ax[0].imshow(wordcloud, interpolation='bilinear')
    ax[0].axis('off')
    
    ax[1].barh(top_nodes[::-1], top_values[::-1], color='teal', alpha=0.6)
    ax[1].tick_params(axis='both', labelsize=12)
    for spine in ax[1].spines.values(): 
        spine.set_visible(False)
    ax[1].get_xaxis().set_ticks([])
    
    # fig.suptitle(title, size=20)
    fig.tight_layout()
    
    if save and save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  ✓ Saved: {save_path}")
    else:
        plt.show()


def plot_communities_distribution(comm_sizes, year, top_n=15):
    """
    Generates the distribution of community sizes. Both individual and
    cummulative nodes.
    """
    percentages = 100 * comm_sizes / sum(comm_sizes)
    top_percentages = percentages.sort_values(ascending=False).head(top_n)
    
    fig, ax = plt.subplots(figsize=(6,3))
    ax.bar(range(1, top_n+1), top_percentages.values, color='teal', alpha=0.6)
    ax.set_xticks(range(1, top_n+1))
    ax.set_xticklabels(top_percentages.index)
    ax.grid(axis='y')
    ax.tick_params(axis='x', labelrotation=0)
    ax.yaxis.set_major_formatter('{x:.0f}%')

    for spine in ax.spines.values(): 
        spine.set_visible(False)
        
    output_dir = "output/images"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    save_filename = f"indiviudal_community_distribution_{year}.png"
    savepath = os.path.join(output_dir, save_filename)
    
    plt.savefig(savepath, bbox_inches='tight')
    print(f"Graph saved in: {savepath}")
    
    plt.show()



    cummulative = [sum(top_percentages[:i]) for i in range(1,top_n+1)]

    fig, ax = plt.subplots(figsize=(6,3))
    ax.bar(range(1, top_n+1), cummulative, color='teal', alpha=0.6)
    ax.set_xticks(range(1, top_n+1))
    ax.grid(axis='y')
    ax.tick_params(axis='x', labelrotation=0)
    ax.set_ylim((0,100))
    ax.yaxis.set_major_formatter('{x:.0f}%')
    for spine in ax.spines.values(): 
        spine.set_visible(False)
    
    save_filename = f"cummulative_community_distribution_{year}.png"
    savepath = os.path.join(output_dir, save_filename)
    
    plt.savefig(savepath, bbox_inches='tight')
    print(f"Graph saved in: {savepath}")
    
    plt.show()
