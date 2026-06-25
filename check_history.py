import requests
r = requests.get("http://127.0.0.1:5000/api/chat/history").json()
print(f"总条数: {len(r['data'])}")
for i, item in enumerate(r["data"][:10]):
    fnames = item.get("file_names") or ([item["file_name"]] if item.get("file_name") else [])
    print(f"[{i+1}] {item['time']}  文件:{fnames}  问题:{item['question'][:35]}")
