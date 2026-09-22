const Api = (() => {
  async function request(path, options = {}) {
    let response;
    try {
      response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        ...options,
      });
    } catch (networkError) {
      throw new ApiError(
        "Не удалось связаться с сервером бюро. Проверьте подключение и попробуйте ещё раз."
      );
    }

    if (response.status === 204) return null;

    let body = null;
    try {
      body = await response.json();
    } catch {
    }

    if (!response.ok) {
      const detail =
        (body && (body.detail || body.message)) ||
        `Сервер ответил с ошибкой (код ${response.status}).`;
      throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail));
    }

    return body;
  }

  class ApiError extends Error {}

  return {
    ApiError,
    getGhosts: () => request("/api/ghosts"),
    createGhost: (data) => request("/api/ghosts", { method: "POST", body: JSON.stringify(data) }),
    deleteGhost: (id) => request(`/api/ghosts/${id}`, { method: "DELETE" }),

    getLocations: () => request("/api/locations"),
    createLocation: (data) => request("/api/locations", { method: "POST", body: JSON.stringify(data) }),
    deleteLocation: (id) => request(`/api/locations/${id}`, { method: "DELETE" }),

    getMatchStatus: () => request("/api/match"),
    runMatching: () => request("/api/match/run", { method: "POST" }),
    manualAssign: (data) => request("/api/match/manual", { method: "POST", body: JSON.stringify(data) }),
    unassign: (ghostId) => request(`/api/match/${ghostId}`, { method: "DELETE" }),

    getReport: () => request("/api/report"),
  };
})();
