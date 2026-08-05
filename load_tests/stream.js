import http from "k6/http";
import { check } from "k6";

export const options = {
  vus: Number(__ENV.VUS || 100),
  duration: __ENV.DURATION || "1m",
  thresholds: { http_req_failed: ["rate<0.01"] },
};

export default function () {
  const response = http.post(
    `${__ENV.BASE_URL}/api/chatbot/stream`,
    JSON.stringify({ message: "hello", user_id: `stream-${__VU}`, history: [] }),
    { headers: { "Content-Type": "application/json", "X-Service-Key": __ENV.SERVICE_KEY } },
  );
  check(response, {
    "stream succeeds": (r) => r.status === 200,
    "stream completes": (r) => r.body.includes('"done": true'),
  });
}
