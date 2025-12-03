//=========1st attmpt result png undhi chudu : ai to work=================================
// const promptEl = document.getElementById("prompt");
// const btn = document.getElementById("btn");
// const out = document.getElementById("output");

// btn.onclick = async () => {
//     out.textContent = "Generating...";
//     const prompt = promptEl.value.trim();

//     const res = await fetch("/generate", {
//         method: "POST",
//         headers: {"Content-Type": "application/json"},
//         body: JSON.stringify({ prompt })
//     });

//     const data = await res.json();
//     out.textContent = data.text || data.raw || JSON.stringify(data, null, 2);
// };
// ================2nd attempt: for it be continous chat==================================================
// const promptEl = document.getElementById("prompt");
// const btn = document.getElementById("btn");
// const chatBox = document.getElementById("chat-box");

// function addMessage(text, type) {
//     const msg = document.createElement("div");
//     msg.classList.add("message", type);
//     msg.textContent = text;
//     chatBox.appendChild(msg);
//     chatBox.scrollTop = chatBox.scrollHeight;
// }

// btn.onclick = async () => {
//     const prompt = promptEl.value.trim();
//     if (!prompt) return;

//     // show user message
//     addMessage(prompt, "user");
//     promptEl.value = "";

//     // call backend
//     const res = await fetch("/generate", {
//         method: "POST",
//         headers: {"Content-Type": "application/json"},
//         body: JSON.stringify({ prompt })
//     });

//     const data = await res.json();
//     addMessage(data.text || data.raw || "No response", "ai");
// };
// ============3rd attempt: for chat to be remeembered========================================
const promptEl = document.getElementById('prompt');
const btn = document.getElementById('btn');
const chatBox = document.getElementById('chat-box');

function addMessage(text, type){
  const el = document.createElement('div');
  el.className = 'message ' + type;
  el.textContent = text;
  chatBox.appendChild(el);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function loadHistory(){
  try{
    const res = await fetch('/history');
    const data = await res.json();
    data.forEach(item => {
      addMessage(item.prompt, 'user');
      addMessage(item.response, 'ai');
    });
  }catch(e){
    console.error(e);
  }
}

btn.addEventListener('click', async () => {
  const prompt = promptEl.value.trim();
  if (!prompt) return;

  addMessage(prompt, 'user');
  promptEl.value = '';

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    });

    const data = await res.json();

    // THIS IS THE FIX — use data.text
    addMessage(data.text || "No response", 'ai');

  } catch (e) {
    addMessage('Error: ' + e.message, 'ai');
  }
});


loadHistory();
