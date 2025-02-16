# Trading Helper API
This is a repo of an API that I created with different end points to assist me in trading stocks and options.

### Reporters
This directory includes code to make financial reports currently it has a DCF report
- uses FMP API needs your free API key in a .ENV 
- value is FMP_API_KEY

### Visuals 
This directory is for charting functions
- stock_visuals charts a stock and draws the following
    - 50 MA
    - 200 Ma
    - Volume

### To Start Python ENV on MAC 
source myenv/bin/activate     

### How to Run 

- Set up ENV variables to FMP API 
    - Value = FMP_API_KEY
- pip install <stuff from requirements.txt>
- python3 api.pi

