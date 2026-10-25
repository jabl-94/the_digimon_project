const TOKEN_KEY = "digifarm_token";
const API_URL_KEY = "digifarm_api_url";
const DEFAULT_API_URL =
  window.DIGIFARM_API_URL ||
  (["localhost", "127.0.0.1"].includes(window.location.hostname)
    ? "http://localhost:8000"
    : window.location.origin);

const loginScreen = document.querySelector("#login-screen");
const dashboardScreen = document.querySelector("#dashboard-screen");
const apiUrlInput = document.querySelector("#api-url");
const tokenInput = document.querySelector("#token-input");
const statusDisplay = document.querySelector("#status-display");
const chatMessages = document.querySelector("#chat-messages");
const notice = document.querySelector("#notice");

function apiBaseUrl() {
  return validateApiUrl(localStorage.getItem(API_URL_KEY) || DEFAULT_API_URL);
}

function showNotice(message) {
  notice.textContent = message;
  notice.classList.toggle("hidden", !message);
}

function showLogin() {
  loginScreen.classList.remove("hidden");
  dashboardScreen.classList.add("hidden");
  apiUrlInput.value = localStorage.getItem(API_URL_KEY) || DEFAULT_API_URL;
}

function showDashboard() {
  loginScreen.classList.add("hidden");
  dashboardScreen.classList.remove("hidden");
  showNotice("");
}

function validateApiUrl(value) {
  const url = new URL(value.trim());
  const isLoopbackHost = ["localhost", "127.0.0.1", "[::1]"].includes(
    url.hostname,
  );
  if (
    !["http:", "https:"].includes(url.protocol) ||
    (url.protocol === "http:" && !isLoopbackHost) ||
    url.username ||
    url.password ||
    (url.pathname !== "/" && url.pathname !== "") ||
    url.search ||
    url.hash
  ) {
    throw new Error(
      "Enter a backend origin using HTTPS. HTTP is allowed only for localhost.",
    );
  }
  return url.origin;
}

function logout() {
  localStorage.removeItem(TOKEN_KEY);
  showLogin();
}

async function apiRequest(endpoint, method = "GET", body = null) {
  const apiUrl = apiBaseUrl();
  const headers = {
    Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) || ""}`,
  };
  const options = { method, headers };
  if (body !== null) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${apiUrl}${endpoint}`, options);
  } catch {
    throw new Error("Could not reach the API. Check its address and your connection.");
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (response.status === 401) {
    logout();
    throw new Error("The token was rejected. Check your token and connect again.");
  }
  if (!response.ok) {
    throw new Error(data.detail || `The API returned an error (${response.status}).`);
  }
  return data;
}

function displayStatus(status) {
  statusDisplay.textContent = JSON.stringify(status, null, 2);
}

function appendChatMessage(speaker, message, className = "") {
  const entry = document.createElement("p");
  entry.className = `chat-message ${className}`.trim();
  const label = document.createElement("strong");
  label.textContent = `${speaker}: `;
  entry.append(label, document.createTextNode(message));
  chatMessages.append(entry);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function fetchStatus() {
  try {
    const status = await apiRequest("/status");
    displayStatus(status);
    showNotice("");
  } catch (error) {
    showNotice(error.message);
  }
}

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showNotice("");

  let apiUrl;
  try {
    apiUrl = validateApiUrl(apiUrlInput.value);
  } catch (error) {
    showNotice(error.message || "Enter a valid backend API address.");
    return;
  }

  const token = tokenInput.value.trim();
  if (token.length < 32) {
    showNotice("The API token must be at least 32 characters.");
    return;
  }

  localStorage.setItem(API_URL_KEY, apiUrl);
  localStorage.setItem(TOKEN_KEY, token);
  tokenInput.value = "";
  showDashboard();
  await fetchStatus();
});

document.querySelector("#logout-button").addEventListener("click", logout);
document.querySelector("#refresh-button").addEventListener("click", fetchStatus);

document.querySelector("#feed-button").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const result = await apiRequest("/feed", "POST");
    displayStatus(result.status);
    showNotice(result.message);
  } catch (error) {
    showNotice(error.message);
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.querySelector("#chat-input");
  const message = input.value.trim();
  if (!message) return;

  appendChatMessage("You", message);
  input.value = "";
  const button = event.currentTarget.querySelector("button");
  button.disabled = true;
  try {
    const result = await apiRequest("/chat", "POST", { message });
    appendChatMessage("Digimon", result.reply, "digimon-message");
    displayStatus(result.status);
    showNotice("");
  } catch (error) {
    appendChatMessage("System", error.message, "error-message");
  } finally {
    button.disabled = false;
    input.focus();
  }
});

if (localStorage.getItem(TOKEN_KEY)) {
  showDashboard();
  fetchStatus();
} else {
  showLogin();
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch((error) => {
      console.error("Could not register the app service worker:", error);
    });
  });
}
