FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
# deno нужен yt-dlp для YouTube
COPY --from=denoland/deno:bin-2.5.6 /deno /usr/local/bin/deno
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot ./bot
CMD ["python", "-m", "bot.main"]
