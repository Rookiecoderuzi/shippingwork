import requests
import time
from typing import Optional, List, Dict

class MinerUClient:
    def __init__(self, api_token: str, base_url: str = "https://mineru.net/api/v4"):
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def submit(self, file_url: str, model_version: str = "pipeline", enable_table: bool = True,
               enable_ocr: bool = True, enable_formula: bool = False, extra_formats: Optional[List[str]] = None,
               page_ranges: Optional[str] = None) -> str:
        """
        提交单文件解析任务
        :param file_url: 要解析的 PDF / 图片 URL
        :param model_version: "pipeline" 或 "vlm"
        :param enable_table: 是否开启表格识别
        :param enable_ocr: 是否开启 OCR
        :param enable_formula: 是否开启公式识别
        :param extra_formats: 可选格式，如 ["docx","html"]
        :param page_ranges: 页码范围字符串，如 "1-5" 或 "2,4-6"
        :return: task_id (字符串)
        """
        url = f"{self.base_url}/extract/task"
        body: Dict = {
            "url": file_url,
            "model_version": model_version,
            "enable_table": enable_table,
            "is_ocr": enable_ocr,
        }
        if enable_formula is not None:
            body["enable_formula"] = enable_formula
        if extra_formats:
            body["extra_formats"] = extra_formats
        if page_ranges:
            body["page_ranges"] = page_ranges

        resp = requests.post(url, headers=self.headers, json=body)
        resp.raise_for_status()
        j = resp.json()
        if j.get("code") not in (0, 200):  # 有时候成功 code 是 0，也可能是 200
            raise RuntimeError(f"MinerU submit failed: {j}")
        return j["data"]["task_id"]

    def submit_batch(self, file_urls: List[str], model_version: str = "pipeline",
                     enable_table: bool = True, enable_ocr: bool = True) -> str:
        """
        批量提交多个文档解析任务
        :param file_urls: URL 列表
        :return: batch_id
        """
        url = f"{self.base_url}/extract/task/batch"
        files = [{"url": u} for u in file_urls]
        body = {
            "files": files,
            "model_version": model_version,
            "enable_table": enable_table,
            "is_ocr": enable_ocr
        }
        resp = requests.post(url, headers=self.headers, json=body)
        resp.raise_for_status()
        j = resp.json()
        if j.get("code") not in (0, 200):
            raise RuntimeError(f"MinerU batch submit failed: {j}")
        return j["data"]["batch_id"]

    def get_task_result(self, task_id: str, wait: bool = True, interval_sec: int = 3,
                        timeout_sec: int = 300) -> Dict:
        """
        查询任务状态 / 获取结果
        :param task_id: 提交任务时返回的 task_id
        :param wait: 是否轮询直到完成
        :param interval_sec: 轮询间隔秒数
        :param timeout_sec: 最多等多久（秒）
        :return: data dict (包含 state, full_zip_url 或错误信息)
        """
        url = f"{self.base_url}/extract/task/{task_id}"
        start = time.time()
        while True:
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            j = resp.json()
            if j.get("code") not in (0, 200):
                raise RuntimeError(f"MinerU query failed: {j}")
            data = j["data"]
            state = data.get("state")
            if state == "done" or state == "failed":
                return data
            if not wait:
                return data
            if time.time() - start > timeout_sec:
                raise TimeoutError("Waiting for task result timed out")
            time.sleep(interval_sec)
if __name__ == "__main__":
    API_TOKEN = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIyNTQwMDM5OCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2NTIxMTAyNywiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiOWI5MzI1ZGQtMzdkMC00ZTkyLWFlNGMtMTQ3ODczN2Q3ZmQyIiwiZW1haWwiOiIiLCJleHAiOjE3NjY0MjA2Mjd9.Xgj_DhM_V-P41swkcEFbT7Ixy3zP-ACn3jX_cmn2ML5IDRY0P05-TcWYMR3T-GSkUNHHEkqZh3W8uKhG2pLDDw"
    client = MinerUClient(API_TOKEN)

    # 提交任务
    task_id = client.submit(
        "https://cdn-mineru.openxlab.org.cn/demo/example.pdf",
        model_version="pipeline",
        enable_table=True,
        enable_ocr=True
    )
    print("Submitted task_id:", task_id)

    # 等待 & 获取结果
    result = client.get_task_result(task_id)
    print("Result:", result)
    if result.get("state") == "done":
        print("Download URL:", result.get("full_zip_url"))
