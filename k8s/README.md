# Production scaling

The manifests split lightweight classification traffic from embedding/RAG traffic.
They assume a production Redis service is reachable at the ConfigMap URI and that
Metrics Server is installed for the HPAs.

Before deployment:

```sh
kubectl create secret generic chatbot-secrets \
  --from-literal=service-api-key='replace-with-a-long-random-secret'
kubectl apply -f k8s/chatbot.yaml
```

Replace the two container image references and the Redis URI first. Route normal
`/respond`, `/stream`, and WebSocket traffic to `chatbot-general`. Route requests
with `use_documents=true`, document operations, and `/summarize` to `chatbot-rag`.

The initial HPA ranges are capacity-test starting points, not universal production
values. Tune requests, limits, replica bounds, and scaling thresholds from
Prometheus results collected during the distributed k6 test.

For the 50,000-user test, install the Grafana k6 operator, then create the script
ConfigMap and launch the 20-runner distributed workload:

```sh
kubectl create configmap chatbot-50k-script \
  --from-file=users_50k.js=load_tests/users_50k.js
kubectl apply -f k8s/k6-50k.yaml
kubectl get testrun chatbot-50k
```

Run this only in an environment sized for the load generators and chatbot pods.
The test ramps gradually, holds 50,000 virtual users for 15 minutes, and fails if
errors reach 1%, p95 exceeds one second, or p99 exceeds two seconds.
