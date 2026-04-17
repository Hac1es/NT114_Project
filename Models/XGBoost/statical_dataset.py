import pandas as pd

# 1. Load the dataset
file_path = '../medeley_dataset.csv'
df = pd.read_csv(file_path)

# 2. Define target quantiles
custom_quantiles = [0.5, 0.75, 0.8, 0.85, 0.9, 0.95]

# 3. Filter for numeric columns
numeric_cols = df.select_dtypes(include=['number']).columns

output_file = "column_unique_statistics.txt"

with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"DETAILED COLUMN FEATURE REPORT (WITH UNIQUE COUNTS)\n")
    f.write(f"Source: {file_path}\n")
    f.write("="*60 + "\n\n")

    for col in numeric_cols:
        # Get standard stats and remove the default 'count' row
        col_stats = df[col].describe().drop('count')
        
        # Calculate unique values count
        unique_count = df[col].nunique()
        
        # Calculate custom quantiles
        col_quantiles = df[col].quantile(custom_quantiles)
        
        # Format the block
        report_block = []
        report_block.append(f"COLUMN: {col}")
        report_block.append("-" * len(f"COLUMN: {col}"))
        report_block.append(f"Unique Values: {unique_count}") # Replaces standard count
        report_block.append(f"\nStandard Metrics:\n{col_stats.to_string()}")
        report_block.append(f"\nCustom Quantiles:")
        report_block.append(col_quantiles.to_string())
        report_block.append("\n" + "="*40 + "\n")
        
        final_block = "\n".join(report_block)
        
        print(final_block)
        f.write(final_block)

print(f"\n[Done] Report with unique counts saved to: {output_file}")