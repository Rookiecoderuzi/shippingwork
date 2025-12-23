import requests
from config import TOKEN, FILE_PATH, MODEL_VERSION, API_UPLOAD_URL, API_EXTRACT_RESULT
import os
import time
import zipfile
import requests
import pandas as pd
import time, threading
import pandas as pd
from openpyxl import Workbook, load_workbook
import os
import re


def apply_upload_url(file_path):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "files": [
            {"name": file_path, "data_id": os.path.basename(file_path)}
        ],
        "model_version": MODEL_VERSION
    }
    print("申请上传 URL ...")
    response = requests.post(API_UPLOAD_URL, headers=headers, json=data)
    response.raise_for_status()
    res = response.json()
    print("返回:", res)
    if res["code"] != 0:
        raise RuntimeError("申请上传 URL 失败: " + res.get("msg", ""))
    return res["data"]["batch_id"], res["data"]["file_urls"]

def upload_file(upload_url, local_file):
    print("上传文件到 OSS ...")
    with open(local_file, "rb") as f:
        res = requests.put(upload_url, data=f)
    if res.status_code == 200:
        print("OSS 上传成功")
    else:
        raise RuntimeError(f"上传 OSS 失败: HTTP {res.status_code}")

def wait_extract_done(batch_id):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    url = f"{API_EXTRACT_RESULT}/{batch_id}"
    print("等待 MinerU 完成解析 ...")
    while True:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()["data"]
        extract_result = data["extract_result"][0]
        state = extract_result["state"]
        print("当前状态:", state)
        if state == "done":
            print("解析完成!")
            return extract_result["full_zip_url"]
        if state == "failed":
            raise RuntimeError("解析失败: " + extract_result.get("err_msg", ""))
        time.sleep(3)

def download_zip(url, save_path):
    print("下载解析 ZIP ...")
    res = requests.get(url)
    with open(save_path, "wb") as f:
        f.write(res.content)
    print("ZIP 下载完成:", save_path)

def unzip_file(zip_path, extract_dir):
    print("解压文件中 ...")

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    print("解压完成:", extract_dir)

def extract_tables_from_html(folder):

    all_tables = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".html") or f.lower().endswith(".md"):
                html_file = os.path.join(root, f)
                print("解析 HTML:", html_file)
                try:
                    with open(html_file, "r", encoding="utf-8") as fp:
                        html_text = fp.read()
                    tables = pd.read_html(html_text)
                    for idx, df in enumerate(tables):
                        all_tables.append({
                            "file": html_file,
                            "index": idx,
                            "data": df
                        })
                except Exception as e:
                    print(f"解析失败: {html_file}，原因: {e}")
    return all_tables

def main():
    # batch_id, urls = apply_upload_url(FILE_PATH)
    # upload_file(urls[0], FILE_PATH)

    # zip_url = wait_extract_done(batch_id)

    # zip_path = f"{batch_id}.zip"
    # download_zip(zip_url, zip_path)

    # extract_dir = f"extract_{batch_id}"
    # unzip_file(zip_path, extract_dir)

    tables_dict = extract_tables_from_html(r"H:\CODE\excel\shipping work\68621c4b-3384-4682-8567-08787522f96e")

    for table in tables_dict:
        print("来源文件:", table["file"])
        print("表格序号:", table["index"])
        print(table["data"])
        table["data"].to_csv(f"test.csv", index=False)
        print("-" * 50)


if __name__ == "__main__":
    main()
