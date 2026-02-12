import pandas as pd
import numpy as np
from datetime import datetime

def analyze_eurusd_data():
    """Load and analyze EURUSD data with detailed statistics"""
    
    # Load data
    data = pd.read_csv("workspace/eurusd_data.csv")
    data['Date'] = pd.to_datetime(data['Date'])
    
    print("=" * 60)
    print("EURUSD DATA ANALYSIS REPORT")
    print("=" * 60)
    
    print(f"\n📊 DATA OVERVIEW")
    print(f"   Period:     {data['Date'].min().date()} to {data['Date'].max().date()}")
    print(f"   Total days: {len(data)}")
    print(f"   Weekdays:   {(data['Date'].dt.dayofweek < 5).sum()} trading days")
    
    print(f"\n📈 PRICE STATISTICS")
    price_cols = ['Open', 'High', 'Low', 'Close']
    
    stats_df = pd.DataFrame({
        'Mean': data[price_cols].mean(),
        'Std': data[price_cols].std(),
        'Min': data[price_cols].min(),
        'Max': data[price_cols].max(),
        'Range': data[price_cols].max() - data[price_cols].min(),
        'Median': data[price_cols].median(),
        'Q1': data[price_cols].quantile(0.25),
        'Q3': data[price_cols].quantile(0.75)
    })
    
    # Format for better display
    for col in ['Mean', 'Std', 'Min', 'Max', 'Range', 'Median', 'Q1', 'Q3']:
        stats_df[col] = stats_df[col].apply(lambda x: f"{x:.5f}")
    
    print(stats_df)
    
    print(f"\n📊 VOLUME ANALYSIS")
    print(f"   Mean Volume:      {data['Volume'].mean():,.0f}")
    print(f"   Std Volume:       {data['Volume'].std():,.0f}")
    print(f"   Min Volume:       {data['Volume'].min():,.0f}")
    print(f"   Max Volume:       {data['Volume'].max():,.0f}")
    print(f"   Total Volume:     {data['Volume'].sum():,.0f}")
    print(f"   Zero Volume Days: {(data['Volume'] == 0).sum()}")
    
    print(f"\n📅 TIME-BASED ANALYSIS")
    data['Month'] = data['Date'].dt.month
    monthly_stats = data.groupby('Month')[['Close', 'Volume']].agg({
        'Close': ['mean', 'std', 'min', 'max'],
        'Volume': 'mean'
    })
    
    print("\nMonthly Average Closing Prices:")
    for month in range(1, 13):
        if month in monthly_stats.index:
            close_mean = monthly_stats.loc[month, ('Close', 'mean')]
            print(f"   Month {month}: {close_mean:.5f}")
    
    print(f"\n📈 DAILY RETURNS ANALYSIS")
    data['Daily_Return'] = data['Close'].pct_change() * 100
    print(f"   Mean Daily Return:    {data['Daily_Return'].mean():.3f}%")
    print(f"   Std Daily Return:     {data['Daily_Return'].std():.3f}%")
    print(f"   Min Daily Return:     {data['Daily_Return'].min():.3f}%")
    print(f"   Max Daily Return:     {data['Daily_Return'].max():.3f}%")
    
    # Positive vs negative days
    positive_days = (data['Daily_Return'] > 0).sum()
    negative_days = (data['Daily_Return'] < 0).sum()
    print(f"   Positive Days:        {positive_days} ({positive_days/len(data)*100:.1f}%)")
    print(f"   Negative Days:        {negative_days} ({negative_days/len(data)*100:.1f}%)")
    
    print(f"\n📊 DATA QUALITY CHECK")
    print(f"   Missing Values:      {data.isnull().sum().sum()}")
    print(f"   Duplicate Dates:     {data['Date'].duplicated().sum()}")
    print(f"   Date Gaps:           {(data['Date'].diff().dt.days > 1).sum()}")
    
    # Save summary to file
    summary = f"""
EURUSD DATA SUMMARY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Period: {data['Date'].min().date()} to {data['Date'].max().date()}
Total Days: {len(data)}

PRICE STATISTICS:
- Open:   Mean={data['Open'].mean():.5f}, Std={data['Open'].std():.5f}
- High:   Mean={data['High'].mean():.5f}, Std={data['High'].std():.5f}
- Low:    Mean={data['Low'].mean():.5f}, Std={data['Low'].std():.5f}
- Close:  Mean={data['Close'].mean():.5f}, Std={data['Close'].std():.5f}

VOLUME STATISTICS:
- Mean Volume: {data['Volume'].mean():,.0f}
- Max Volume:  {data['Volume'].max():,.0f}
- Total Volume: {data['Volume'].sum():,.0f}

DAILY RETURNS:
- Mean Return: {data['Daily_Return'].mean():.3f}%
- Std Return:  {data['Daily_Return'].std():.3f}%
- Min/Max:     {data['Daily_Return'].min():.3f}% / {data['Daily_Return'].max():.3f}%
"""
    
    with open("workspace/eurusd_summary.txt", "w") as f:
        f.write(summary)
    
    print(f"\n✓ Analysis complete! Summary saved to workspace/eurusd_summary.txt")
    return data

if __name__ == "__main__":
    analyze_eurusd_data()