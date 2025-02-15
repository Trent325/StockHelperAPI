import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# Ask the user for the stock symbol
stock = input("Enter the stock symbol (e.g., AAPL for Apple, TSLA for Tesla): ").upper()

# Ask the user to choose a time frame
time_frame = input("Select a time frame (3m, 6m, 1y, 5y): ").lower()

# Get today's date
today = datetime.today()

# Determine the end date (most recent market day)
end_date = today.strftime('%Y-%m-%d')

# Calculate the start date based on the selected time frame
if time_frame == '3m':
    start_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
elif time_frame == '6m':
    start_date = (today - timedelta(days=180)).strftime('%Y-%m-%d')
elif time_frame == '1y':
    start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
elif time_frame == '5y':
    start_date = (today - timedelta(days=365*5)).strftime('%Y-%m-%d')
else:
    print("Invalid time frame selected. Please use 3m, 6m, 1y, or 5y.")
    exit()

try:
    # Fetch additional historical data for better MA calculation
    extended_start_date = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=200)).strftime('%Y-%m-%d')
    df = yf.download(stock, start=extended_start_date, end=end_date, progress=False)
    
    # Fix the MultiIndex columns
    df = df.droplevel(0, axis=1)
    df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
    
    # Calculate moving averages on the extended data
    df['MA50'] = df['Close'].rolling(window=50, min_periods=1).mean()
    df['MA200'] = df['Close'].rolling(window=200, min_periods=1).mean()
    
    # Trim the data back to the requested date range
    df = df[start_date:]
    
    print("\nFixed DataFrame Head:")
    print(df.head())
    print("\nColumns:", df.columns.tolist())
    
    if df.empty:
        print(f"Could not fetch data for {stock}. Please check the stock symbol and dates.")
        exit()

    # Create figure
    fig = go.Figure()

    # Add candlestick trace
    candlestick = go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='OHLC',
        showlegend=True
    )
    fig.add_trace(candlestick)

    # Add MA traces
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MA50'],
        name='50-day MA',
        line=dict(color='blue', width=1.5),
        showlegend=True
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MA200'],
        name='200-day MA',
        line=dict(color='orange', width=1.5),
        showlegend=True
    ))

    # Add volume trace
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        name='Volume',
        marker=dict(
            color=['red' if close < open else 'green' 
                   for close, open in zip(df['Close'], df['Open'])],
        ),
        opacity=0.5,
        yaxis='y2',
        showlegend=True
    ))

    # Update layout for fullscreen
    fig.update_layout(
        title=dict(
            text=f'{stock} Stock Price Chart',
            x=0.5,
            font=dict(size=24)
        ),
        yaxis=dict(
            title='Price',
            side='left',
            showgrid=True
        ),
        yaxis2=dict(
            title='Volume',
            side='right',
            overlaying='y',
            showgrid=False,
        ),
        xaxis=dict(
            title='Date',
            rangeslider=dict(visible=False)
        ),
        legend=dict(
            x=1.1,
            y=0.9
        ),
        # Make chart fullscreen
        autosize=True,
        height=1000,  # Increased height
        margin=dict(l=50, r=50, t=50, b=50),  # Reduced margins
        paper_bgcolor='white',
        plot_bgcolor='white',
        showlegend=True,
        hovermode='x unified'
    )

    # Add custom HTML template for fullscreen
    template = '''
    <html>
        <head>
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    overflow: hidden;
                }
                #chart {
                    width: 100vw;
                    height: 100vh;
                }
            </style>
        </head>
        <body>
            <div id="chart">
                {plot_div}
            </div>
        </body>
    </html>
    '''

    # Save and display the chart
    output_filename = f"{stock}_stock_chart_{start_date}_to_{end_date}.html"
    fig.write_html(
        output_filename,
        full_html=True,
        include_plotlyjs=True,
        default_width='100%',
        default_height='100%',
        config={'displayModeBar': True, 'scrollZoom': True},
        post_script="document.getElementsByClassName('js-plotly-plot')[0].style.height = '100vh';",
    )
    fig.show()
    
    print(f"\nChart saved as {output_filename}")

except Exception as e:
    print(f"Error occurred: {str(e)}")
    import traceback
    print("\nFull error traceback:")
    print(traceback.format_exc())