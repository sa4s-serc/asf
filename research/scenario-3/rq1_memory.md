====================================================================================================
MEMORY EVALUATION – Aggregated Results
====================================================================================================
Logs aggregated: 3
  - scenario-3_20251014_034628.json
  - scenario-3_20251014_035554.json
  - scenario-3_20251014_035735.json

Total memory queries: 9
Average required coverage ratio: 0.89
Average optional coverage ratio: 0.25
Average mechanism score: 0.58
Average precision: 75.56%
Average recall: 50.66%
Average F1: 51.32%
Average BLEU: 46.38%
Overall memory score: 0.72

Required Categories (average hit %)
+----------+-------+--------------------------------------+
| Category | Hit % | Description                          |
+----------+-------+--------------------------------------+
| baseline | 100.0 | Performance baselines and thresholds |
| change   | 100.0 | Recent configuration changes         |
| topology |  66.7 | Network topology and CIDRs           |
+----------+-------+--------------------------------------+

Optional Categories (average hit %)
+-------------------+-------+------------------------------------------------+
| Category          | Hit % | Description                                    |
+-------------------+-------+------------------------------------------------+
| policy            |   0.0 | Troubleshooting / scaling guardrails           |
| incident_response |   0.0 | Incident response workflows                    |
| infrastructure    | 100.0 | Service-to-database dependencies               |
| failure_pattern   |   0.0 | Known failure patterns / symptom vs root cause |
+-------------------+-------+------------------------------------------------+

Per-mechanism Averages
+------------+-------------+-------------+----------+-------+--------+
| Mechanism  | Avg queries | Precision % | Recall % |  F1 % | BLEU % |
+------------+-------------+-------------+----------+-------+--------+
| temporal   |        1.00 |      100.00 |    29.77 | 45.63 |  78.02 |
| multi_hop  |        1.00 |      100.00 |    26.47 | 41.77 |  81.31 |
| overall    |        3.00 |       75.56 |    50.66 | 51.32 |  46.38 |
| single_hop |        2.00 |       63.33 |    61.11 | 54.17 |  30.56 |
+------------+-------------+-------------+----------+-------+--------+

Reference signals seeded for each mechanism:
  - single_hop: baseline_response_time, security_group_id, payment_service_subnet, database_subnet
  - multi_hop: change, topology
  - temporal: 2024-01-15T08:15:00Z, 08:15
  - causal_chain: symptom vs root cause, databaseconnectiontimeout, retry overhead

====================================================================================================
====================================================================================================
MEMORY EVALUATION – scenario-3_20251014_034628.json
====================================================================================================
Total memory queries: 3
Required coverage hit ratio: 1.00
Optional coverage hit ratio: 0.25
Mechanism average score: 0.62
Average precision: 53.33%
Average recall: 43.14%
Average F1: 40.15%
Average BLEU: 39.52%
Overall memory score: 0.72

Required Categories
+----------+-----+--------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Category | Hit | Description                          | Sample memories                                                                                                                                                                                                                                    |
+----------+-----+--------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| baseline |  ✓  | Performance baselines and thresholds | payment-service baseline performance: avg_response_time=1.5s, p95_response_time=2.1s, p99_response_time=3.2s, error_rate; payment-service performance thresholds: response_time degradation > 30% triggers alert, error_rate > 2% triggers investi |
| change   |  ✓  | Recent configuration changes         | change chg-2024-0108-007 at 2024-01-08t16:30:00z: infrastructure_scaling of payment-service by devops@company.com - scal; timeline of recent changes: jan 8 (scaling), jan 10 (code deployment v2.3.1), jan 15 08:15 am (security group modificati |
| topology |  ✓  | Network topology and CIDRs           | subnet details for payment-service: application instances run in app_tier subnet 10.0.2.0/24 in availability zone us-eas                                                                                                                           |
+----------+-----+--------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Optional Categories (bonus credit)
+-------------------+-----+------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Category          | Hit | Description                                    | Sample memories                                                                                                                                                                                                                                    |
+-------------------+-----+------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| policy            |  ✗  | Troubleshooting / scaling guardrails           | —                                                                                                                                                                                                                                                  |
| incident_response |  ✗  | Incident response workflows                    | —                                                                                                                                                                                                                                                  |
| infrastructure    |  ✓  | Service-to-database dependencies               | payment-service infrastructure: runs on 3 m5.xlarge ec2 instances (i-abc123, i-abc124, i-abc125) in subnet 10.0.2.0/24, ; payment-service uses connection pooling with 3 retry attempts per database operation, timeout=10 seconds per attempt, to |
| failure_pattern   |  ✗  | Known failure patterns / symptom vs root cause | —                                                                                                                                                                                                                                                  |
+-------------------+-----+------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Retrieval Mechanisms (per-query metrics)
+------------+---------+-------------+----------+-------+--------+
| Mechanism  | Queries | Precision % | Recall % |  F1 % | BLEU % |
+------------+---------+-------------+----------+-------+--------+
| overall    |       3 |       53.33 |    43.14 | 40.15 |  39.52 |
| single_hop |       2 |       30.00 |    50.00 | 37.50 |  18.75 |
| multi_hop  |       1 |      100.00 |    29.41 | 45.45 |  81.05 |
| temporal   |       1 |      100.00 |    29.41 | 45.45 |  81.05 |
+------------+---------+-------------+----------+-------+--------+

Retrieval Quality Metrics
+-----------+-----------+
| Metric    | Average % |
+-----------+-----------+
| Precision |     53.33 |
| Recall    |     43.14 |
| F1        |     40.15 |
| BLEU-1    |     39.52 |
+-----------+-----------+
====================================================================================================
====================================================================================================
MEMORY EVALUATION – scenario-3_20251014_035554.json
====================================================================================================
Total memory queries: 3
Required coverage hit ratio: 0.67
Optional coverage hit ratio: 0.25
Mechanism average score: 0.50
Average precision: 86.67%
Average recall: 56.57%
Average F1: 59.44%
Average BLEU: 48.12%
Overall memory score: 0.65

Required Categories
+----------+-----+--------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Category | Hit | Description                          | Sample memories                                                                                                                                                                                                                                    |
+----------+-----+--------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| baseline |  ✓  | Performance baselines and thresholds | prod-payment-db baseline metrics: cpu_utilization=30-40%, active_connections=40-60, connection_utilization=8-12%, query_; payment-service baseline performance: avg_response_time=1.5s, p95_response_time=2.1s, p99_response_time=3.2s, error_rate |
| change   |  ✓  | Recent configuration changes         | change chg-2024-0108-007 at 2024-01-08t16:30:00z: infrastructure_scaling of payment-service by devops@company.com - scal; change chg-2024-0110-003 at 2024-01-10t14:00:00z: code_deployment of payment-service v2.3.1 by ci-cd-pipeline - routine  |
| topology |  ✗  | Network topology and CIDRs           | —                                                                                                                                                                                                                                                  |
+----------+-----+--------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Optional Categories (bonus credit)
+-------------------+-----+------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Category          | Hit | Description                                    | Sample memories                                                                                                                                                                                                                                    |
+-------------------+-----+------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| policy            |  ✗  | Troubleshooting / scaling guardrails           | —                                                                                                                                                                                                                                                  |
| incident_response |  ✗  | Incident response workflows                    | —                                                                                                                                                                                                                                                  |
| infrastructure    |  ✓  | Service-to-database dependencies               | payment-service infrastructure: runs on 3 m5.xlarge ec2 instances (i-abc123, i-abc124, i-abc125) in subnet 10.0.2.0/24, ; prod-payment-db configuration: postgresql rds instance in subnet 10.0.3.0/24 (database_tier), protected by security grou |
| failure_pattern   |  ✗  | Known failure patterns / symptom vs root cause | —                                                                                                                                                                                                                                                  |
+-------------------+-----+------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Retrieval Mechanisms (per-query metrics)
+------------+---------+-------------+----------+-------+--------+
| Mechanism  | Queries | Precision % | Recall % |  F1 % | BLEU % |
+------------+---------+-------------+----------+-------+--------+
| overall    |       3 |       86.67 |    56.57 | 59.44 |  48.12 |
| single_hop |       2 |       80.00 |    66.67 | 62.50 |  36.46 |
| temporal   |       1 |      100.00 |    36.36 | 53.33 |  71.43 |
+------------+---------+-------------+----------+-------+--------+

Retrieval Quality Metrics
+-----------+-----------+
| Metric    | Average % |
+-----------+-----------+
| Precision |     86.67 |
| Recall    |     56.57 |
| F1        |     59.44 |
| BLEU-1    |     48.12 |
+-----------+-----------+
====================================================================================================
====================================================================================================
MEMORY EVALUATION – scenario-3_20251014_035735.json
====================================================================================================
Total memory queries: 3
Required coverage hit ratio: 1.00
Optional coverage hit ratio: 0.25
Mechanism average score: 0.62
Average precision: 86.67%
Average recall: 52.29%
Average F1: 54.37%
Average BLEU: 51.50%
Overall memory score: 0.81

Required Categories
+----------+-----+--------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Category | Hit | Description                          | Sample memories                                                                                                                                                                                                                                    |
+----------+-----+--------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| baseline |  ✓  | Performance baselines and thresholds | prod-payment-db baseline metrics: cpu_utilization=30-40%, active_connections=40-60, connection_utilization=8-12%, query_; payment-service baseline performance: avg_response_time=1.5s, p95_response_time=2.1s, p99_response_time=3.2s, error_rate |
| change   |  ✓  | Recent configuration changes         | change chg-2024-0108-007 at 2024-01-08t16:30:00z: infrastructure_scaling of payment-service by devops@company.com - scal; timeline of recent changes: jan 8 (scaling), jan 10 (code deployment v2.3.1), jan 15 08:15 am (security group modificati |
| topology |  ✓  | Network topology and CIDRs           | subnet details for payment-service: application instances run in app_tier subnet 10.0.2.0/24 in availability zone us-eas                                                                                                                           |
+----------+-----+--------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Optional Categories (bonus credit)
+-------------------+-----+------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------+
| Category          | Hit | Description                                    | Sample memories                                                                                                          |
+-------------------+-----+------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------+
| policy            |  ✗  | Troubleshooting / scaling guardrails           | —                                                                                                                        |
| incident_response |  ✗  | Incident response workflows                    | —                                                                                                                        |
| infrastructure    |  ✓  | Service-to-database dependencies               | payment-service infrastructure: runs on 3 m5.xlarge ec2 instances (i-abc123, i-abc124, i-abc125) in subnet 10.0.2.0/24,  |
| failure_pattern   |  ✗  | Known failure patterns / symptom vs root cause | —                                                                                                                        |
+-------------------+-----+------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------+

Retrieval Mechanisms (per-query metrics)
+------------+---------+-------------+----------+-------+--------+
| Mechanism  | Queries | Precision % | Recall % |  F1 % | BLEU % |
+------------+---------+-------------+----------+-------+--------+
| overall    |       3 |       86.67 |    52.29 | 54.37 |  51.50 |
| single_hop |       2 |       80.00 |    66.67 | 62.50 |  36.46 |
| multi_hop  |       1 |      100.00 |    23.53 | 38.10 |  81.58 |
| temporal   |       1 |      100.00 |    23.53 | 38.10 |  81.58 |
+------------+---------+-------------+----------+-------+--------+

Retrieval Quality Metrics
+-----------+-----------+
| Metric    | Average % |
+-----------+-----------+
| Precision |     86.67 |
| Recall    |     52.29 |
| F1        |     54.37 |
| BLEU-1    |     51.50 |
+-----------+-----------+
====================================================================================================
