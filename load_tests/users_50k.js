import http from "k6/http";
import { check, sleep } from "k6";

const targetUsers = Number(__ENV.TARGET_USERS || 50000);

export const options = {
  scenarios: {
    concurrent_users: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: __ENV.RAMP_1 || "5m", target: Math.ceil(targetUsers * 0.1) },
        { duration: __ENV.RAMP_2 || "5m", target: Math.ceil(targetUsers * 0.5) },
        { duration: __ENV.RAMP_3 || "10m", target: targetUsers },
        { duration: __ENV.HOLD || "15m", target: targetUsers },
        { duration: "5m", target: 0 },
      ],
      gracefulRampDown: "2m",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000", "p(99)<2000"],
    checks: ["rate>0.99"],
  },
};

export default function () {
  const userId = `scale-user-${__VU}`;
  const response = http.post(
    `${__ENV.BASE_URL}/api/chatbot/respond`,
    JSON.stringify({
      message: "hello there",
      user_id: userId,
      history: [],
    }),
    {
      headers: {
        "Content-Type": "application/json",
        "X-Service-Key": __ENV.SERVICE_KEY,
      },
      tags: { workload: "general-response" },
    },
  );
  check(response, {
    "status is 200": (result) => result.status === 200,
    "response has intent": (result) => Boolean(result.json("intent")),
  });
  sleep(Number(__ENV.THINK_TIME_SECONDS || 30));
}
