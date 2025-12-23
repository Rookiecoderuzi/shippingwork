import requests
from utils.config import TOKEN, FILE_PATH, MODEL_VERSION, API_UPLOAD_URL, API_EXTRACT_RESULT
import os
import time
import zipfile
import requests
import pandas as pd
import time, threading
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


# ---------------------------
#  上传文件 PUT
# ---------------------------

def upload_file(upload_url, local_file):
    print("上传文件到 OSS ...")
    with open(local_file, "rb") as f:
        res = requests.put(upload_url, data=f)

    if res.status_code == 200:
        print("OSS 上传成功")
    else:
        raise RuntimeError(f"上传 OSS 失败: HTTP {res.status_code}")


# ---------------------------
#  轮询解析状态
# ---------------------------

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


# ---------------------------
#  下载 ZIP
# ---------------------------

def download_zip(url, save_path):
    print("下载解析 ZIP ...")
    res = requests.get(url)
    with open(save_path, "wb") as f:
        f.write(res.content)
    print("ZIP 下载完成:", save_path)


# ---------------------------
#  解压 ZIP
# ---------------------------

def unzip_file(zip_path, extract_dir):
    print("解压文件中 ...")

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    print("解压完成:", extract_dir)


# ---------------------------
#  从 HTML 中提取表格
# ---------------------------

def extract_tables_from_html(folder):
    print("解析 HTML 表格 ...")

    results = {}

    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".html"):
                html_file = os.path.join(root, f)
                print("解析 HTML:", html_file)

                try:
                    tables = pd.read_html(html_file)
                    results[html_file] = tables
                except Exception as e:
                    print(f"解析失败: {html_file}，原因: {e}")

    return results


# ---------------------------
#  导出所有表格到一个 Excel
# ---------------------------

def export_tables_to_excel(tables_dict, excel_path):
    print("正在导出到 Excel:", excel_path)

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for html_file, tables in tables_dict.items():
            base = os.path.splitext(os.path.basename(html_file))[0]

            for i, df in enumerate(tables):
                sheet_name = f"{base}_T{i}"
                sheet_name = sheet_name[:31]  # Excel sheet 名最大 31 字符

                df.to_excel(writer, sheet_name=sheet_name, index=False)

    print("Excel 导出完成:", excel_path)


# ---------------------------
#  主流程
# ---------------------------

def main():
    batch_id, urls = apply_upload_url(FILE_PATH)
    upload_file(urls[0], FILE_PATH)

    zip_url = wait_extract_done(batch_id)

    zip_path = f"{batch_id}.zip"
    download_zip(zip_url, zip_path)

    extract_dir = f"extract_{batch_id}"
    unzip_file(zip_path, extract_dir)

    tables_dict = extract_tables_from_html(extract_dir)

    excel_output = f"{batch_id}_tables.xlsx"
    export_tables_to_excel(tables_dict, excel_output)

    print("\n🎉 全流程完成！Excel 已生成：", excel_output)


if __name__ == "__main__":
    main()
