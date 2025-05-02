# 파일: run_pipeline.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # 현재 경로
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 상위 루트

import os
import subprocess

# print("====== [1/4] 리뷰 및 가게 정보 크롤링 시작 ======")
# subprocess.run(["python", "crawler/kakao_crawling.py"])

# print("====== [2/4] 리뷰 전처리 및 JSON 생성 ======")
# subprocess.run(["python", "preprocessing/reviews_to_clean.py"])
# subprocess.run(["python", "preprocessing/stores_menus_to_json.py"])

# print("====== [3/4] 리뷰 임베딩 및 ChromaDB 생성 ======")
# subprocess.run(["python", "vectordb/embed_reviews.py"])

print("====== [4/4] Gradio 챗봇 실행 ======")
subprocess.run(["python", "chatbot/app.py"])
