import requests

r = requests.post("http://127.0.0.1:5173/api/test_buy", json={"symbol":"NIFTY", "option_type":"CE", "ltp":100.0})
print(r.status_code)
print(r.text)
