import yfinance as yf
import matplotlib.pyplot as plt
import mplcyberpunk
from datetime import datetime

def plot_stock_mplcyberpunk(ticker: str):
    # Fetch 1-year historical data
    data = yf.Ticker(ticker)
    hist = data.history(period="1y")

    # Apply cyberpunk style
    plt.style.use("cyberpunk")

    # Plot the stock closing prices
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(hist.index, hist["Close"], label=f"{ticker} Close Price", linewidth=2.5)

    # Enhance labels and title
    ax.set_title(f"{ticker} Stock Price – Last 1 Year", fontsize=18, weight='bold')
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (USD)")
    ax.legend(loc="upper left")

    # Add cyberpunk glow effects
    mplcyberpunk.add_glow_effects()

    # Save the graph
    date_str = datetime.now().strftime("%Y-%m-%d")
    img_path = f"{ticker}_{date_str}_1y_cyberpunk.png"
    plt.tight_layout()
    plt.savefig(img_path, dpi=300)
    plt.close()

    return img_path
