CREATE OR REPLACE TABLE measurements AS SELECT * FROM read_json_auto('latency-rows.json.gz');
SELECT backend,n,filtered,ef,count(*) AS samples,
      round(avg(recall_at_10),4) AS recall_at_10,
      round(quantile_cont(ms,0.5),3) AS median_ms,
      round(quantile_cont(ms,0.95),3) AS p95_ms,
      min(returned) AS minimum_returned
      FROM measurements GROUP BY ALL ORDER BY n,filtered,ef,backend;
