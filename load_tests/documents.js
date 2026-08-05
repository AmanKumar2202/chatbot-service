import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    document_uploads: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 5),
      timeUnit: "1s",
      duration: __ENV.DURATION || "1m",
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
};

export default function () {
  const id = `${__VU}-${__ITER}`;
  const response = http.post(
    `${__ENV.BASE_URL}/api/chatbot/documents`,
    JSON.stringify({
      doc_id: `load-${id}`,
      filename: "load.txt",
      user_id: `document-user-${__VU}`,
      text: "A representative document sentence. ".repeat(100),
    }),
    { headers: { "Content-Type": "application/json", "X-Service-Key": __ENV.SERVICE_KEY } },
  );
  check(response, { "document indexed": (r) => r.status === 200 });
}
