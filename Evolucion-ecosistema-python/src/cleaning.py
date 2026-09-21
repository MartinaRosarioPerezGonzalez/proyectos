import pandas as pd
import re
import os
import ast
import numpy as np

def clean_dataframe(data):
    """
    Clean and process package dependency data from a dataframe or parquet file.
    
    Args:
        data: Path to parquet file (str) or pandas DataFrame
        
    Returns:
        pd.DataFrame: Cleaned dataframe with columns 'package_name' and 'requirement'
    """
    # If it's a path to parquet, load as dataframe
    if isinstance(data, str) and data.endswith('.parquet'):
        df = pd.read_parquet(data)
    else:
        df = data
    
    datadict = {"package": [], "requirement": [], "version": []}

    for _, row in df.iterrows():
        pkg = row["name"]
        ver = row["version"]
        reqs = row["requires_dist"]

        # Convert to list if it's a string
        if isinstance(reqs, str):
            try:
                reqs = ast.literal_eval(reqs)
            except Exception:
                # If not a list, treat the string as a single dependency
                reqs = [reqs]
        elif isinstance(reqs, float) or reqs is None:
            reqs = []

        # Ensure it's a list
        if not isinstance(reqs, (list, tuple, np.ndarray)):
            reqs = [reqs]

        # If empty or contains only NaN
        if len(reqs) == 0 or all(pd.isna(x) for x in reqs):       
            datadict["package"].append(pkg)
            datadict["requirement"].append(np.nan)
            datadict["version"].append(ver)
            continue

        # Process dependencies
        for req in reqs:
            if not isinstance(req, str) or req.strip() == "":
                continue
            dep_name = (
                req.split(";")[0]
                .split("[")[0]
                .split("==")[0]
                .split(">=")[0]
                .split("<=")[0]
                .split(">")[0]
                .split("<")[0]
                .split(" (")[0]
                .strip()
            )
            datadict["package"].append(pkg)
            datadict["requirement"].append(dep_name)
            datadict["version"].append(ver)
    
    # Create dataframe and apply clean() function to package names
    result = pd.DataFrame(datadict)
    result['clean_package'] = result['package'].apply(clean)
    
    # Standardize the dataframe with only the necessary columns
    final_result = result[['clean_package', 'requirement']].rename(
        columns={'clean_package': 'package_name'}
    )
    
    return final_result

def clean(name):
    """
    Clean and normalize a package name by removing version suffixes,
    qualifiers, and standardizing the format.
    
    Args:
        name: Package name to clean
        
    Returns:
        str: Cleaned package name
    """
    # If the value is nan, return None
    if pd.isna(name):
        return None
    s = str(name).strip().lower()
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s)
    v = re.compile(r'[-_.](?:v?\d[\w.\-!,+]*|r\d+|rev\d+)$', flags=re.I)
    # Use while loop in case there are multiple suffixes
    while v.search(s):
        s = v.sub('', s)

    s = re.sub(r'-[0-9a-f]{6,40}$', '', s, flags=re.I)
    s = re.sub(r'[-_.][ab]\d+$', '', s, flags=re.I)
    qualifier = re.compile(
        r'[-_.](?:dev|devel|alpha|beta|rc|pre|post|final|snapshot|nightly|'
        r'unreleased|unofficial|unofficialdev|master|visimus|essex)$',
        flags=re.I
    )
    while qualifier.search(s):
        s = qualifier.sub('', s)

    s = re.sub(r'[-_.]v?\d[\w.\-+]*\s+(?:alpha|beta|rc|dev|devel)\d*$', '', s, flags=re.I)
    s = re.sub(r'[-_.]+$', '', s)
    s = re.sub(r'^([a-z0-9._-]+)-\1$', r'\1', s)
    return s

def process_package_file(data_path, output_path=None):
    """
    Load and process package dependency data from a file.
    
    Args:
        data_path: Path to CSV or parquet file
        output_path: Optional path to save the processed dataframe as CSV
        
    Returns:
        pd.DataFrame: Cleaned dataframe with columns 'package_name' and 'requirement'
    """
    if data_path.endswith('.parquet'):
        df = clean_dataframe(data_path)
    elif data_path.endswith('.csv'):
        df = pd.read_csv(data_path)
    else:
        raise ValueError("File must be CSV or Parquet")
    
    if output_path:
        df.to_csv(output_path, index=False)
    
    return df
