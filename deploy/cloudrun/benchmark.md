# Phase 0 Cloud Run benchmark record

Status: template only; deployment requires the owner checkpoint.

| Metric | Result | Evidence / command |
| --- | --- | --- |
| Region | TBD | `gcloud run services describe` |
| Image digest | TBD | Artifact Registry |
| Image size | TBD | Artifact Registry |
| Cold start | TBD | first `/health` request timing |
| Idle memory / CPU | TBD | Cloud Monitoring |
| Peak memory / CPU | TBD | Cloud Monitoring during representative job |
| Processing time | TBD | job stage timings |
| Input / output bytes | TBD | request and artifact metrics |
| Estimated cost | TBD | project pricing inputs |

No benchmark result is considered complete until it is tied to a deployed
revision and a representative fixture/job.
