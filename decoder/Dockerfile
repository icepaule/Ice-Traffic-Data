FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fetch_asn.sh .
RUN ./fetch_asn.sh && rm -rf asn/*/.git
COPY its_decoder its_decoder
VOLUME /data
EXPOSE 8097
CMD ["python", "-m", "its_decoder.main"]
