# Phase 0 Cloud Run experiment

This directory contains configuration only. It does not deploy anything and
contains no provider credentials.

The local API smoke check is separate from this experiment: it verifies the
FastAPI process and OpenAPI surface, but it is not evidence that the container
image builds or that Cloud Run can execute it.

Replace the image placeholders in `service.yaml.template`, then deploy only
after the owner approves the Google Cloud project, billing, APIs, Artifact
Registry repository, and service account.

```bash
gcloud run services replace deploy/cloudrun/service.yaml \
  --region REGION \
  --project PROJECT_ID
```

Supply secrets through the approved secret mechanism (for example
`--set-secrets`) if a real provider test is authorized. Never add secret
values to this YAML, the image, or command history.

Record the experiment in the benchmark note with:

- image digest and compressed image size;
- cold-start and health latency;
- idle and peak memory/CPU;
- representative job duration and input/output bytes;
- estimated cost and known blockers.
