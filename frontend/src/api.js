const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

async function request(path, options) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail
      : Array.isArray(detail) ? "Check the brief: one or more fields are invalid."
      : detail?.message ?? "Request failed.";
    const error = new Error(`${message}${detail?.code ? ` (${detail.code})` : ""}${detail?.request_id ? ` Request: ${detail.request_id}` : ""}`);
    throw error;
  }

  return response.json();
}

export function listCampaigns() {
  return request("/api/campaigns");
}

export function createCampaign(payload) {
  return request("/api/campaigns", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateCampaign(campaignId) {
  return request(`/api/campaigns/${campaignId}/generate`, {
    method: "POST",
  });
}


export function getConfig() {
  return request("/api/config");
}
