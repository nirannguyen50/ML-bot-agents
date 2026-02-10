import yfinance as yf
import pandas as pd
print("Testing yfinance download for AAPL...")
try:
    df = yf.download("AAPL", period="1mo", progress=False)
    if df.empty:
        print("Result: Empty DataFrame")
    else:
        print(f"Result: Success ({len(df)} rows)")
        print(df.head())
except Exception as e:
    print(f"Result: Error - {e}")
