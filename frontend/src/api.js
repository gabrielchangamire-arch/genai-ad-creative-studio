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
    throw new Error(body?.detail ?? "Request failed.");
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

