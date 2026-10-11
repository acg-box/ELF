CREATE OR REPLACE TABLE answers AS SELECT * FROM read_json_auto('answer-rows.json.gz');
SELECT condition,count(*) AS completed,
          count(*) FILTER (WHERE split != 'dev') AS scored,
          sum(strict_correct::INTEGER) FILTER (WHERE split != 'dev') AS strict_correct,
          sum(reviewed_correct::INTEGER) FILTER (WHERE split != 'dev') AS reviewed_correct,
          sum(reviewed_correct::INTEGER) AS all_reviewed_correct,
          avg(context_tokens) AS mean_context_tokens,quantile_cont(seconds,0.5) AS median_seconds,
          sum(paid_usd) AS paid_usd,sum(prompt_tokens) AS prompt_tokens,
          sum(completion_tokens) AS completion_tokens,sum(cached_tokens) AS cached_tokens
          FROM answers GROUP BY condition ORDER BY condition;
