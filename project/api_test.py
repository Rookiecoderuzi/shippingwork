import requests

token = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIyNTQwMDM5OCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2NTIxMTAyNywiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiOWI5MzI1ZGQtMzdkMC00ZTkyLWFlNGMtMTQ3ODczN2Q3ZmQyIiwiZW1haWwiOiIiLCJleHAiOjE3NjY0MjA2Mjd9.Xgj_DhM_V-P41swkcEFbT7Ixy3zP-ACn3jX_cmn2ML5IDRY0P05-TcWYMR3T-GSkUNHHEkqZh3W8uKhG2pLDDw"
# url = "https://mineru.net/api/v4/file-urls/batch"
# header = {
#     "Content-Type": "application/json",
#     "Authorization": f"Bearer {token}"
# }
# data = {
#     "files": [
#         {"name":r"H:\CODE\excel\shipping work\EXCEL\SE128076.pdf", "data_id": "SE128076"}
#     ],
#     "model_version":"vlm"
# }
# file_path = [r"H:\CODE\excel\shipping work\EXCEL\SE128076.pdf"]
# try:
#     response = requests.post(url,headers=header,json=data)
#     if response.status_code == 200:
#         result = response.json()
#         print('response success. result:{}'.format(result))
#         if result["code"] == 0:
#             batch_id = result["data"]["batch_id"]
#             urls = result["data"]["file_urls"]
#             print('batch_id:{},urls:{}'.format(batch_id, urls))
#             for i in range(0, len(urls)):
#                 with open(file_path[i], 'rb') as f:
#                     res_upload = requests.put(urls[i], data=f)
#                     if res_upload.status_code == 200:
#                         print(f"{urls[i]} upload success")
#                     else:
#                         print(f"{urls[i]} upload failed")
#         else:
#             print('apply upload url failed,reason:{}'.format(result.msg))
#     else:
#         print('response not success. status:{} ,result:{}'.format(response.status_code, response))
# except Exception as err:
#     print(err)
    
    

url = f"https://mineru.net/api/v4/extract-results/batch/ed07b64a-4de2-4de2-8108-89dfc89ca14b"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

res = requests.get(url, headers=header)
print(res.status_code)
print(res.json())
print(res.json()["data"])