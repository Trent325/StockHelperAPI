from flask import Flask, request, jsonify, Response
from flasgger import Swagger
import yfinance as yf
from src.reporters.news import get_stock_news  
from src.reporters.dcf import run_dcf
from src.reporters.earnings import get_earnings_yfinance
from src.visuals.stock_visual import generate_stock_chart

app = Flask(__name__)
swagger = Swagger(app) 

@app.route('/api/get_stock_news', methods=['GET'])
def api_get_stock_news():
    """
    Get latest stock news for a given ticker.
    ---
    parameters:
      - name: ticker
        in: query
        type: string
        required: true
        description: Stock ticker symbol (e.g., AAPL, TSLA)
    responses:
      200:
        description: A list of news articles related to the stock
        schema:
          type: array
          items:
            type: object
            properties:
              title:
                type: string
              link:
                type: string
              source:
                type: string
              published_date:
                type: string
      400:
        description: Ticker is required
      404:
        description: No news found for the ticker
    """
    ticker = request.args.get('ticker', '').upper()  # Retrieve ticker from query parameters
    if not ticker:
        return jsonify({"error": "Ticker is required!"}), 400

    # Call the function to get the stock news
    news_data = get_stock_news(ticker)
    
    # Return the news data as JSON
    if isinstance(news_data, dict) and "message" in news_data:
        # If the response is a message (error), return that
        return jsonify(news_data), 404
    
    return jsonify(news_data)

@app.route('/api/get_dcf', methods=['GET'])
def dcf_valuation():
    """
    Get DCF (Discounted Cash Flow) valuation for a stock.
    ---
    parameters:
      - name: ticker
        in: query
        type: string
        required: true
        description: Stock ticker symbol
    responses:
      200:
        description: DCF valuation result
        schema:
          type: object
          properties:
            fair_value:
              type: number
            current_price:
              type: number
            recommendation:
              type: string
      400:
        description: Ticker symbol is required
    """
    ticker = request.args.get('ticker', default='', type=str).upper()  # Get ticker from query params
    if not ticker:
        return jsonify({"error": "Ticker symbol is required"}), 400
    
    result = run_dcf(ticker)
    
    # Return the result as a JSON response
    return jsonify(result)

@app.route('/api/earnings', methods=['GET'])
def earnings():
    """
    Get earnings data for a stock.
    ---
    parameters:
      - name: ticker
        in: query
        type: string
        required: true
        description: Stock ticker symbol
    responses:
      200:
        description: Earnings data
        schema:
          type: object
          properties:
            revenue:
              type: number
            net_income:
              type: number
            eps:
              type: number
      400:
        description: Ticker symbol is required
    """
    ticker = request.args.get('ticker', default='', type=str).upper()  # Get ticker from query params
    if not ticker:
        return jsonify({"error": "Ticker symbol is required"}), 400
    
    result = get_earnings_yfinance(ticker)
    
    # Return the result as a JSON response
    return jsonify(result)

@app.route('/generate_stock_chart', methods=['GET'])
def generate_chart():
    """
    Generate a stock price chart.
    ---
    parameters:
      - name: ticker
        in: query
        type: string
        required: true
        description: Stock ticker symbol
      - name: time_frame
        in: query
        type: string
        required: true
        description: Time frame for the chart (e.g., 1d, 1w, 1m)
    responses:
      200:
        description: HTML chart visualization
        content:
          text/html:
            schema:
              type: string
      400:
        description: Missing required parameters
      500:
        description: Internal server error
    """
    # Extract query parameters (ticker and time_frame)
    ticker = request.args.get('ticker')
    time_frame = request.args.get('time_frame')

    if not ticker or not time_frame:
        return jsonify({"error": "Missing required parameters: 'ticker' or 'time_frame'"}), 400

    try:
        # Generate the chart HTML (without saving it to a file)
        chart_html = generate_stock_chart(ticker, time_frame)

        # Return the chart HTML as a response
        return Response(chart_html, content_type='text/html')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stocks/options", methods=["GET"])
def get_options_activity():
    """
    Get unusual options activity for a given stock.
    ---
    parameters:
      - name: ticker
        in: query
        type: string
        required: true
        description: Stock ticker symbol (e.g., AAPL, TSLA)
    responses:
      200:
        description: Unusual options activity
        schema:
          type: object
          properties:
            symbol:
              type: string
            expiration_date:
              type: string
            unusual_calls:
              type: array
              items:
                type: object
                properties:
                  contractSymbol:
                    type: string
                  strike:
                    type: number
                  lastPrice:
                    type: number
                  volume:
                    type: number
                  openInterest:
                    type: number
                  volumeOIratio:
                    type: number
            unusual_puts:
              type: array
              items:
                type: object
                properties:
                  contractSymbol:
                    type: string
                  strike:
                    type: number
                  lastPrice:
                    type: number
                  volume:
                    type: number
                  openInterest:
                    type: number
                  volumeOIratio:
                    type: number
      400:
        description: Missing or invalid ticker parameter
      404:
        description: No options data available
      500:
        description: Internal server error
    """

    ticker = request.args.get("ticker", "").upper()
    
    if not ticker:
        return jsonify({"error": "Ticker is required!"}), 400

    try:
        stock = yf.Ticker(ticker)
        options_dates = stock.options  # List of available expiration dates
        
        if not options_dates:
            return jsonify({"error": "No options data available"}), 404

        # Fetch options for the nearest expiration date
        expiration_date = options_dates[0]
        options_chain = stock.option_chain(expiration_date)
        calls = options_chain.calls
        puts = options_chain.puts

        # Filter for unusual activity: high volume/open interest ratio
        def filter_unusual_options(df):
            df["volumeOIratio"] = df["volume"] / (df["openInterest"] + 1)  # Prevent division by zero
            return df[df["volumeOIratio"] > 2]  # Threshold for unusual activity

        unusual_calls = filter_unusual_options(calls)
        unusual_puts = filter_unusual_options(puts)

        return jsonify({
            "symbol": ticker,
            "expiration_date": expiration_date,
            "unusual_calls": unusual_calls.to_dict(orient="records"),
            "unusual_puts": unusual_puts.to_dict(orient="records"),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
