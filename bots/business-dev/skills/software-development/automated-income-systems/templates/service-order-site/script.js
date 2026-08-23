// === CONFIG — EDIT THIS ===
// Your WhatsApp number in international format, digits only (no +, no spaces).
// Example: 919345568244  (that's +91 93455 68244)
const WHATSAPP_NUMBER = "919999999999";

// Price map per package value (used only for the message text)
const priceMap = {
  "Tier1 (Rs499)": "Rs499",
  "Tier2 (Rs1999/5)": "Rs1999",
  "Tier3 (Rs7999/30)": "Rs7999",
  "Custom": "To be discussed",
};

function buildMessage() {
  const name = document.getElementById("custName").value.trim() || "-";
  const phone = document.getElementById("custPhone").value.trim() || "-";
  const pack = document.getElementById("packSelect").value;
  const vidType = document.getElementById("vidType").value;
  const details = document.getElementById("scriptText").value.trim() || "-";
  const price = priceMap[pack] || "";
  return [
    "New order - YOUR BRAND",
    "",
    "Name: " + name,
    "WhatsApp: " + phone,
    "Package: " + pack + (price ? " (" + price + ")" : ""),
    "Type: " + vidType,
    "Details:",
    details,
  ].join("\n");
}

document.getElementById("year").textContent = new Date().getFullYear();

document.querySelectorAll(".pack a[data-pack]").forEach((a) => {
  a.addEventListener("click", () => {
    document.getElementById("packSelect").value = a.dataset.pack;
  });
});

document.getElementById("orderForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const url = "https://wa.me/" + WHATSAPP_NUMBER + "?text=" + encodeURIComponent(buildMessage());
  window.open(url, "_blank");
});

document.getElementById("copyUpi").addEventListener("click", () => {
  const id = document.getElementById("upiId").textContent;
  navigator.clipboard?.writeText(id).then(() => {
    const btn = document.getElementById("copyUpi");
    const old = btn.textContent; btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = old), 1500);
  });
});
