const $ = (id) => document.getElementById(id);
let ready = false,
  requestKey = crypto.randomUUID(),
  version = 0;
const money = (n) => new Intl.NumberFormat("ru-RU").format(n) + " ₽";
async function api(path, payload) {
  const response = await fetch(
    path,
    payload
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      : {},
  );
  const data = await response.json();
  if (!response.ok) throw Error(data.error);
  return data;
}
async function updateQuote() {
  const current = ++version;
  try {
    const data = await api("/api/quote", { device: $("device").value, issue: $("issue").value });
    if (current === version)
      $("quote-price").textContent = money(data.min) + " – " + money(data.max);
  } catch (e) {
    if (current === version) $("quote-price").textContent = "Расчёт недоступен";
  }
}
async function init() {
  try {
    const data = await api("/api/config");
    for (const [id, list] of [
      ["device", data.devices],
      ["issue", data.issues],
    ]) {
      for (const [key, item] of Object.entries(list)) {
        const option = document.createElement("option");
        option.value = key;
        option.textContent = item.label;
        $(id).append(option);
      }
      $(id).addEventListener("change", updateQuote);
    }
    ready = true;
    await updateQuote();
  } catch (e) {
    $("quote-price").textContent = "Ошибка подключения";
    $("submit").disabled = true;
  }
}
document.querySelectorAll("[data-device]").forEach(
  (button) =>
    (button.onclick = () => {
      if (ready) {
        $("device").value = button.dataset.device;
        updateQuote();
        $("estimate").scrollIntoView({ behavior: "smooth" });
      }
    }),
);
$("request-form").onsubmit = async (e) => {
  e.preventDefault();
  if (!ready) return;
  const form = new FormData(e.target);
  const payload = Object.fromEntries(form);
  payload.consent = form.has("consent");
  payload.device = $("device").value;
  payload.issue = $("issue").value;
  payload.request_key = requestKey;
  $("submit").disabled = true;
  $("form-status").hidden = true;
  try {
    const data = await api("/api/requests", payload);
    $("form-status").className = "";
    $("form-status").textContent =
      `Заявка ${data.id} сохранена.\nОриентир по работе: ${money(data.quote.min)} – ${money(data.quote.max)}.\nОбращение появилось на доске заявок мастерской. Время визита пока не назначено.`;
    $("form-status").hidden = false;
    requestKey = crypto.randomUUID();
    e.target.reset();
  } catch (error) {
    $("form-status").className = "error";
    $("form-status").textContent = error.message;
    $("form-status").hidden = false;
  } finally {
    $("submit").disabled = false;
  }
};
init();
