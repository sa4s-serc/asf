==========================================================================================
SCENARIO 2 – Aggregated Evaluation
==========================================================================================
Logs aggregated: 3
  - scenario-2_20251014_034519.json
  - scenario-2_20251014_034908.json
  - scenario-2_20251014_035353.json

+----------------------------+----------+-----------+
| Metric                     |  Default | Framework |
+----------------------------+----------+-----------+
| Task completion            |     100% |      100% |
| Tool usage (used/expected) | 10.67/11 |  10.67/11 |
| Tool sequence              |        — |       33% |
| Expected tool calls        |        — |       67% |
| Policy guardrail query     |        — |      100% |
| Dependency guardrail query |        — |        0% |
| Memory precision (mean %)  |        — |     30.00 |
| Memory recall (mean %)     |        — |     13.14 |
| Memory F1 (mean %)         |        — |     18.09 |
| Memory BLEU (mean %)       |        — |     25.98 |
| Permission question rate   |        — |         — |
+----------------------------+----------+-----------+

Expected tools:
  - check_bucket_public_access
  - get_bucket_policy
  - get_bucket_tags
  - assess_data_exposure
  - check_application_dependencies
  - enable_access_logging
  - enable_versioning
  - update_bucket_policy
  - verify_authorized_access
  - log_security_incident
  - notify_security_team

Tools used per run:
  scenario-2_20251014_034519.json: check_bucket_public_access, assess_data_exposure, get_bucket_tags, check_application_dependencies, enable_access_logging, enable_versioning, update_bucket_policy, verify_authorized_access, log_security_incident, notify_security_team
  scenario-2_20251014_034908.json: check_bucket_public_access, assess_data_exposure, get_bucket_tags, check_application_dependencies, enable_access_logging, enable_versioning, get_bucket_policy, update_bucket_policy, verify_authorized_access, log_security_incident, notify_security_team
  scenario-2_20251014_035353.json: check_bucket_public_access, assess_data_exposure, get_bucket_tags, check_application_dependencies, enable_access_logging, enable_versioning, get_bucket_policy, update_bucket_policy, verify_authorized_access, log_security_incident, notify_security_team
==========================================================================================
