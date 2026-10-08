FROM python:3.11-bookworm

ARG MEMOS_REVISION=a7367d07e55db61099f7b4e2c1108bc5831a24f3
RUN git init /opt/memos \
  && git -C /opt/memos remote add origin https://github.com/MemTensor/MemOS.git \
  && git -C /opt/memos fetch --depth=1 origin "${MEMOS_REVISION}" \
  && git -C /opt/memos checkout --detach FETCH_HEAD \
  && test "$(git -C /opt/memos rev-parse HEAD)" = "${MEMOS_REVISION}"

COPY config/benchmark/locks/memos.txt /opt/benchmark/locks/memos.txt
RUN pip install --no-cache-dir --require-hashes --requirement /opt/benchmark/locks/memos.txt \
  && mkdir -p /benchmark/state/files

ENV PYTHONPATH=/opt/memos/src
ENV FILE_LOCAL_PATH=/benchmark/state/files
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "memos.api.server_api:app", "--host", "0.0.0.0", "--port", "8000"]
