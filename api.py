from flask import Flask, request, jsonify, Response
from src.reporters.news import get_stock_news  
from src.reporters.dcf import run_dcf
from src.reporters.earnings import get_earnings_yfinance
from src.visuals.stock_visual import generate_stock_chart

app = Flask(__name__)

@app.route('/api/get_stock_news', methods=['GET'])
def api_get_stock_news():
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
    ticker = request.args.get('ticker', default='', type=str).upper()  # Get ticker from query params
    if not ticker:
        return jsonify({"error": "Ticker symbol is required"}), 400
    
    result = run_dcf(ticker)
    
    # Return the result as a JSON response
    return jsonify(result)

@app.route('/api/earnings', methods=['GET'])
def earnings():
    ticker = request.args.get('ticker', default='', type=str).upper()  # Get ticker from query params
    if not ticker:
        return jsonify({"error": "Ticker symbol is required"}), 400
    
    result = get_earnings_yfinance(ticker)
    
    # Return the result as a JSON response
    return jsonify(result)

@app.route('/generate_stock_chart', methods=['GET'])
def generate_chart():
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


if __name__ == "__main__":
    app.run(debug=True)
