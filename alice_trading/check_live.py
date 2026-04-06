import urllib.request, json, time
time.sleep(3)
r = urllib.request.urlopen('http://localhost:8001/api/v1/dashboard/metrics')
d = json.loads(r.read())
print('data_engine_status:', d.get('data_engine_status'))
mkt = d.get('market_data', {})
for k, v in mkt.items():
    print(f"  {k}: ltp={v.get('ltp')} status={v.get('status')}")

print("\n--- SERVER LOGS ---")
rl = urllib.request.urlopen('http://localhost:8001/api/v1/alerts/logs')
logs = json.loads(rl.read())
for log in logs[-15:]:
    print(f"[{log.get('timestamp')}] {log.get('message')}")
