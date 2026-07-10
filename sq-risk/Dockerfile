# 使用官方的 Python 執行環境作為基底
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 將 requirements.txt 複製到容器內並安裝依賴套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 將專案的所有程式碼複製到容器內
COPY . .

# 暴露你的應用程式使用的 Port
EXPOSE 5000

# 設定環境變數，告訴 Flask 哪個是主程式
ENV FLASK_APP=app.py

# 設定容器啟動時要執行的指令 (綁定到 0.0.0.0 才能從外部存取)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
