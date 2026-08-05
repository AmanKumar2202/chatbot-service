import http from "k6/http";
import { check } from "k6";

export const options = { vus: 20, iterations: 120 };

export default function () {
  const userId = `quota-user-${__VU % 2}`;
  const response = http.post(
    `${__ENV.BASE_URL}/api/chatbot/respond`,
    JSON.stringify({ message: "hello", user_id: userId, history: [] }),
    { headers: { "Content-Type": "application/json", "X-Service-Key": __ENV.SERVICE_KEY } },
  );
  check(response, { "accepted or limited": (r) => r.status === 200 || r.status === 429 });
}

export function handleSummary(data) {
  return { stdout: JSON.stringify(data.metrics.http_reqs, null, 2) };
}
