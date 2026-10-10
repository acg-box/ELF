FROM elf-benchmark-http:v8
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils tesseract-ocr tesseract-ocr-chi-sim \
    fonts-wqy-zenhei python3-reportlab python3-pil \
    && rm -rf /var/lib/apt/lists/*
