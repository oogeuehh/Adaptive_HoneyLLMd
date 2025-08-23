import pandas as pd
import json
from collections import defaultdict

INPUT_FILE = "macro_path_micro_stats.csv"
OUTPUT_FILE = "hpa.json"

def build_hpa(df):
    hpa = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    # iterate dataframe
    for _, row in df.iterrows():
        position = int(row["position"])
        macro = row["macro"]
        micro = row["micro"] if pd.notna(row["micro"]) else "none"
        count = int(row["count"])

        if "count" not in hpa[position][macro][micro]:
            hpa[position][macro][micro]["count"] = 0
        hpa[position][macro][micro]["count"] += count

    # compute probability
    for position in hpa:
        for macro in hpa[position]:
            total_count = sum(hpa[position][macro][micro]["count"] for micro in hpa[position][macro])
            for micro in hpa[position][macro]:
                hpa[position][macro][micro]["prob"] = (
                    hpa[position][macro][micro]["count"] / total_count
                    if total_count > 0 else 0
                )

    return hpa

def main():
    df = pd.read_csv(INPUT_FILE)
    hpa = build_hpa(df)

    hpa_dict = {str(pos): dict(macros) for pos, macros in hpa.items()}

    with open(OUTPUT_FILE, "w") as f:
        json.dump(hpa_dict, f, indent=4)

    print(f"HPA JSON saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
