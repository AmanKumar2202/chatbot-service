import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    sustained_respond: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 100),
      timeUnit: "1s",
      duration: __ENV.DURATION || "2m",
      preAllocatedVUs: 100,
      maxVUs: 1000,
    },
  },
  thresholds: { http_req_failed: ["rate<0.01"], http_req_duration: ["p(95)<500"] },
};

export default function () {
  const userId = `load-user-${__VU}`;
  const response = http.post(
    `${__ENV.BASE_URL}/api/chatbot/respond`,
    JSON.stringify({ message: "hello there", user_id: userId, history: [] }),
    { headers: { "Content-Type": "application/json", "X-Service-Key": __ENV.SERVICE_KEY } },
  );
  check(response, { "respond succeeds": (r) => r.status === 200 });
}
