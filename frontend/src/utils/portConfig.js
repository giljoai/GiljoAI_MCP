/** Derive the API port from the current page URL, falling back to 7272. */
export const getApiPort = () =>
  import.meta.env.VITE_API_PORT || window.API_PORT || window.location.port || '7272'

export const getApiPortInt = () => parseInt(getApiPort(), 10)
