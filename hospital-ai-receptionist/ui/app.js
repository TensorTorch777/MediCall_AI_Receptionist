const API_BASE = "http://localhost:8000";

const orb = document.getElementById("siriOrb");
const statusText = document.getElementById("statusText");
const chatLog = document.getElementById("chatLog");
const bookBtn = document.getElementById("bookBtn");

let recognition;
let listening = false;
let flowStarted = false;
let history = [];

function setOrb(mode, status) {
  orb.className = `siri-orb ${mode}`;
  statusText.textContent = status;
}

function addMsg(role, text) {
  const el = document.createElement("div");
  el.className = `msg ${role === "user" ? "user" : "ai"}`;
  el.textContent = text;
  chatLog.appendChild(el);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function speak(text) {
  return new Promise((resolve) => {
    if (!window.speechSynthesis) return resolve();
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1;
    utter.pitch = 1;
    utter.onstart = () => setOrb("speaking", "Aria is speaking...");
    utter.onend = () => {
      if (listening) {
        setOrb("listening", "Listening...");
      } else {
        setOrb("idle", "Ready");
      }
      resolve();
    };
    window.speechSynthesis.speak(utter);
  });
}

async function callChat(message) {
  const payload = { message, history };
  const res = await fetch(`${API_BASE}/conversation/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("Chat API failed");
  return res.json();
}

async function finalizeConversation() {
  const res = await fetch(`${API_BASE}/conversation/finalize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ history })
  });
  if (!res.ok) throw new Error("Finalize API failed");
  return res.json();
}

async function sendMessage(message) {
  if (!message?.trim()) return;
  addMsg("user", message);
  history.push({ role: "user", content: message });
  setOrb("idle", "Thinking...");
  try {
    const data = await callChat(message);
    const reply = data.reply;
    addMsg("assistant", reply);
    history.push({ role: "assistant", content: reply });
    await speak(reply);
  } catch (err) {
    addMsg("assistant", "Sorry, I could not reach the AI service.");
    setOrb("idle", "API error");
  }
}

function initSpeechRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    statusText.textContent = "Browser speech recognition unavailable. Use typing.";
    micBtn.disabled = true;
    return;
  }
  recognition = new SR();
  recognition.lang = "en-US";
  recognition.continuous = true;
  recognition.interimResults = false;

  recognition.onstart = () => {
    listening = true;
    bookBtn.disabled = true;
    setOrb("listening", "Listening...");
  };

  recognition.onresult = async (event) => {
    const i = event.results.length - 1;
    if (!event.results[i].isFinal) return;
    const text = event.results[i][0].transcript.trim();
    if (!text) return;
    const lower = text.toLowerCase();
    if (lower.includes("goodbye") || lower.includes("bye") || lower.includes("quit")) {
      addMsg("user", text);
      history.push({ role: "user", content: text });
      recognition.stop();
      setOrb("idle", "Saving to Sheets...");
      try {
        const out = await finalizeConversation();
        addMsg("assistant", "Thank you for calling City Hospital! Have a wonderful day and take care.");
        if (out.extracted) {
          addMsg("assistant", `Saved details for ${out.extracted.full_name || "patient"}${out.appointment_id ? ` | Appointment: ${out.appointment_id}` : ""}`);
        }
        setOrb("idle", "Saved. Click Book an Appointment for a new call.");
      } catch (e) {
        addMsg("assistant", "Could not save details to Sheets right now.");
        setOrb("idle", "Save failed. Click Book an Appointment to retry.");
      } finally {
        bookBtn.disabled = false;
        flowStarted = false;
      }
      return;
    }
    await sendMessage(text);
  };

  recognition.onend = () => {
    listening = false;
    if (!flowStarted) setOrb("idle", "Ready");
  };
}

bookBtn.addEventListener("click", async () => {
  if (!recognition || flowStarted) return;
  flowStarted = true;
  history = [];
  chatLog.innerHTML = "";
  addMsg("assistant", "Welcome to City Hospital. My name is Aria, and I'll be happy to help you with your appointment. Can you please tell me your full name so I can look up your information?");
  await speak("Welcome to City Hospital. My name is Aria, and I'll be happy to help you with your appointment. Can you please tell me your full name so I can look up your information?");
  try {
    recognition.start();
  } catch {
    flowStarted = false;
    bookBtn.disabled = false;
  }
});

initSpeechRecognition();
setOrb("idle", "Click 'Book an Appointment' to begin");
