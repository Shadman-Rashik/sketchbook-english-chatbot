/* Sketchbook front-end: one page, five animated screens. No build step, no framework. */
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch {} },
};

let sid = store.get('sb_sid', '');
if (!/^[A-Za-z0-9_-]{8,64}$/.test(sid)) {
  sid = (crypto.randomUUID ? crypto.randomUUID() : Date.now() + Math.random().toString(16).slice(2)).replace(/[^A-Za-z0-9_-]/g, '');
  store.set('sb_sid', sid);
}
let name = store.get('sb_name', '');
let voiceOn = true, state = null, busy = false, quiz = null, attempt = 0, locked = false, screen = 'splash';

const MODES = { learn: '🌱 Learning', chat: '💬 Chatting', engage: '🎈 Fun time', support: '🤗 Here for you' };
const MOODS = [['happy', '😄'], ['excited', '🤩'], ['calm', '😌'], ['tired', '🥱'], ['sad', '😢'], ['angry', '😠']];
const LEVELS = [[1, 'Little Sprout', 0], [2, 'Word Explorer', 6], [3, 'Sentence Star', 14]];

/* ---------- origami crane (8 pieces that "unfold" as stars grow) ---------- */
const PIECES = [ // [fill, points, unfold order]
  ['#a8bdd6', '10,40 60,75 40,85', 2], ['#c9d7e8', '40,85 60,75 100,100 80,112', 3],
  ['#dcc3a3', '85,72 125,12 135,70', 6], ['#f6e6d2', '60,75 130,70 100,100', 0],
  ['#93abc8', '80,112 100,100 128,106 100,122', 1], ['#f8dcc4', '70,76 125,12 112,92', 7],
  ['#f2cfb4', '130,70 165,25 150,75', 4], ['#e9a98b', '165,25 190,32 160,38', 5],
];
function crane(on = 8) {
  const polys = PIECES.map(([f, p, o]) => `<polygon class="p ${o < on ? '' : 'off'}" fill="${f}" points="${p}"/>`).join('');
  return `<svg class="crane" viewBox="0 0 200 140" role="img" aria-label="Origami crane">${polys}</svg>`;
}

/* ---------- helpers ---------- */
async function api(path, body) {
  const r = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : undefined);
  if (!r.ok) throw new Error(r.status);
  return r.json();
}
function toast(t) { const el = $('#toast'); el.textContent = t; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 2200); }
function burst(el) {
  const b = el.getBoundingClientRect(), bits = ['✨', '⭐', '🌸', '🎈', '💛'];
  for (let i = 0; i < 14; i++) {
    const s = document.createElement('span'); s.className = 'bit'; s.textContent = bits[i % bits.length];
    s.style.left = b.left + b.width / 2 + 'px'; s.style.top = b.top + b.height / 2 + 'px';
    s.style.setProperty('--dx', (Math.random() * 220 - 110) + 'px'); s.style.setProperty('--dy', (Math.random() * -160 - 20) + 'px');
    s.style.setProperty('--rot', (Math.random() * 360 - 180) + 'deg');
    document.body.append(s); setTimeout(() => s.remove(), 950);
  }
}
function speak(t, force) {
  if ((!voiceOn && !force) || !('speechSynthesis' in window)) return;
  try {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(t.replace(/[\u{1F300}-\u{1FAFF}☀-➿]/gu, ''));
    const v = speechSynthesis.getVoices().find((x) => /en[-_]US/i.test(x.lang) && /female|samantha|zira|google/i.test(x.name)) ||
      speechSynthesis.getVoices().find((x) => /^en/i.test(x.lang));
    if (v) u.voice = v;
    u.lang = 'en-US'; u.rate = 0.88; u.pitch = 1.25; speechSynthesis.speak(u);
  } catch {}
}

/* ---------- navigation ---------- */
function show(id) {
  screen = id;
  $$('.screen').forEach((s) => s.classList.toggle('active', s.id === 's-' + id));
  $('#nav').hidden = id === 'splash';
  $$('#nav button').forEach((b) => b.classList.toggle('on', b.dataset.go === id));
  if (id === 'chat' && !$('#msgs').children.length) greet();
  if (id === 'play' && !quiz) loadQuiz();
  if (id === 'play' && quiz) renderStats();
}
document.addEventListener('click', (e) => {
  const g = e.target.closest('[data-go]'); if (!g) return;
  const go = g.dataset.go;
  if (go === 'learn') { sendChat('Teach me a new word'); } else show(go);
});

/* ---------- live clock ---------- */
function tick() {
  const d = new Date(), h = d.getHours();
  $('#partday').textContent = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : h < 21 ? 'Good evening' : 'Good night';
  $('#datetime').textContent = d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }) + ' · ' +
    d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  $('#hH').setAttribute('transform', `rotate(${(h % 12) * 30 + d.getMinutes() / 2} 32 32)`);
  $('#hM').setAttribute('transform', `rotate(${d.getMinutes() * 6} 32 32)`);
}
setInterval(tick, 1000); tick();

/* Word of the day: curriculum POOLS, index from local calendar date (no API). */
const WOTD = [
  ['apple', '🍎'], ['cat', '🐱'], ['dog', '🐶'], ['ball', '⚽'], ['sun', '🌞'],
  ['fish', '🐟'], ['car', '🚗'], ['tree', '🌳'], ['bird', '🐦'], ['book', '📖'],
  ['one', '1️⃣'], ['two', '2️⃣'], ['three', '3️⃣'], ['hello', '👋'],
  ['big', '🐘'], ['small', '🐭'], ['hot', '🔥'], ['cold', '🧊'],
  ['happy', '😊'], ['friend', '🤝'], ['jump', '🤸'], ['water', '💧'],
  ['mom', '👩'], ['sleep', '😴'],
];
function wordOfTheDay() {
  const d = new Date();
  const i = (d.getFullYear() * 372 + (d.getMonth() + 1) * 31 + d.getDate()) % WOTD.length;
  return { key: WOTD[i][0], emoji: WOTD[i][1] };
}
function renderWotd() {
  const w = wordOfTheDay();
  $('#wotdEmo').textContent = w.emoji;
  $('#wotdWord').textContent = w.key;
}
renderWotd();
$('#wotdSay').onclick = () => speak(wordOfTheDay().key, true);
$('#wotdPractice').onclick = async () => {
  const w = wordOfTheDay();
  if (busy) return;
  busy = true;
  try {
    const r = await api('/api/practice', { session_id: sid, word: w.key, name });
    show('chat');
    addMsg('bot', r.reply);
    setMode(r.mode, r.reason);
    defaultChips();
    state = r.state; renderStats(); speak(r.reply);
  } catch { toast('Dora is sleepy. Try again!'); }
  busy = false;
};

/* ---------- state rendering ---------- */
function renderStats() {
  if (!state) return;
  const s = state, lv = LEVELS[s.level - 1];
  $('#lvChip').textContent = `L${s.level} · ${s.level_name}`;
  $('#starChip').textContent = '⭐ ' + s.stars; $('#pStars').textContent = '⭐ ' + s.stars;
  $('#plvl').textContent = `L${s.level} · ${s.level_name}`;
  const lo = lv[2], hi = s.next_at || lo + 10;
  $('#lvFill').style.width = (s.next_at ? Math.min(100, ((s.stars - lo) / (hi - lo)) * 100) : 100) + '%';
  $('#hello').textContent = `Hello, ${name || 'Little Explorer'} ✧`;
  $('#progCrane').innerHTML = crane(Math.max(1, Math.round(8 * s.crane)));
  $('#lvName').textContent = `Level ${s.level} · ${s.level_name}`;
  $('#toNext').textContent = s.next_at ? `${s.next_at - s.stars} more ⭐ to level ${s.level + 1}` : 'You reached the top level! 🎉';
  $('#path').innerHTML = LEVELS.map(([n, nm]) => `<div class="node ${s.level >= n ? 'on' : ''}"><b>L${n}</b>${nm}</div>`).join('');
  const rows = [['Thinking', s.cognitive, '#a8bdd6'], ['Feelings', s.sel.awareness, '#f1b3a0'], ['Confidence', s.sel.confidence, '#b9d2bd'],
    ['Curiosity', s.sel.curiosity, '#d8cfee'], ['Kindness', s.sel.kindness, '#f5c542']];
  $('#bars').innerHTML = rows.map(([l, v, c]) => `<div class="row"><span>${l}</span><div class="track"><i style="width:${v}%;background:${c}"></i></div><em>${v}</em></div>`).join('');
  $('#note').textContent = s.insight;
}
function levelUp(st) {
  $('#ovCrane').innerHTML = crane(Math.max(1, Math.round(8 * st.crane)));
  $('#ovT').textContent = `Level ${st.level}!`;
  $('#ovP').textContent = `You are a ${st.level_name} now. Your crane grew! 🎉`;
  $('#ov').hidden = false; speak(`Level ${st.level}! You are a ${st.level_name}!`);
}
$('#ovOk').onclick = () => { $('#ov').hidden = true; };

/* ---------- chat ---------- */
const msgs = $('#msgs');
function scrollDown() { msgs.scrollTo({ top: msgs.scrollHeight, behavior: 'smooth' }); }
function addMsg(role, text) {
  const d = document.createElement('div'); d.className = `m ${role} clay ${role === 'bot' ? 'soft' : 'blue'}`; d.textContent = text;
  msgs.append(d); scrollDown(); return d;
}
function typing() { const d = document.createElement('div'); d.className = 'm bot clay soft typing'; d.innerHTML = '<i></i><i></i><i></i>'; msgs.append(d); scrollDown(); return d; }
function setMode(m, why) {
  const b = $('#modeBadge'); b.dataset.mode = m; b.textContent = MODES[m] || MODES.chat; $('#why').textContent = why ? `Dora noticed: ${why}` : '';
}
function quickChips(list) {
  $('#quick').innerHTML = '';
  list.forEach(([label, fn]) => { const b = document.createElement('button'); b.className = 'q'; b.textContent = label; b.onclick = fn; $('#quick').append(b); });
}
const defaultChips = () => quickChips([
  ['🌱 Teach me a word', () => sendChat('Teach me a new word')], ['🎈 Let\'s play', () => sendChat('Let\'s play a game')],
  ['😄 I feel happy', () => sendChat('I feel happy today')], ['😢 I feel sad', () => sendChat('I feel sad')]]);
function greet() {
  const t = `Hi ${name || 'friend'}! I'm Dora. 🌸 Tell me how you feel, or ask me to teach you a word!`;
  addMsg('bot', t); defaultChips(); setMode('chat', ''); speak(t);
}
function addBreathe() {
  const d = document.createElement('div'); d.className = 'breathe clay soft';
  d.innerHTML = '<div class="orb"></div><span>Breathe in… and out…</span>'; msgs.append(d); scrollDown();
  setTimeout(() => d.classList.add('done'), 14000);
}
async function sendChat(text) {
  text = (text || '').trim(); if (!text || busy) return;
  busy = true; show('chat'); addMsg('me', text); $('#quick').innerHTML = '';
  const t = typing(), t0 = performance.now();
  try {
    const r = await api('/api/chat', { session_id: sid, message: text, name });
    const wait = Math.max(0, 450 - (performance.now() - t0)); await new Promise((ok) => setTimeout(ok, wait)); // gentle pacing, not counted in latency
    t.remove(); const el = addMsg('bot', r.reply);
    setMode(r.mode, r.reason);
    $('#lat').textContent = `⚡ ${Math.round(performance.now() - t0 - wait)} ms · ${r.source === 'llm' ? 'AI' : r.source === 'safety' ? 'safe' : r.source === 'praise' ? 'instant' : 'quick'}`;
    if (r.mode === 'support') addBreathe();
    defaultChips();
    if (r.suggest === 'play') quickChips([['🎈 Open Play', () => show('play')], ['🌱 Teach me a word', () => sendChat('Teach me a new word')]]);
    if (r.praised) burst(el);
    state = r.state; renderStats(); speak(r.reply);
    if (r.leveled_up) setTimeout(() => levelUp(r.state), 700);
  } catch { t.remove(); addMsg('bot', 'Oops, I got sleepy. 😴 Please try again!'); defaultChips(); }
  busy = false;
}
$('#chatForm').onsubmit = (e) => { e.preventDefault(); const v = $('#chatIn').value; $('#chatIn').value = ''; sendChat(v); };
$('#askForm').onsubmit = (e) => { e.preventDefault(); const v = $('#askIn').value; $('#askIn').value = ''; sendChat(v || 'Hello Dora'); };
$('#voiceBtn').onclick = () => { voiceOn = !voiceOn; $('#voiceBtn').textContent = voiceOn ? '🔊' : '🔇'; if (!voiceOn) speechSynthesis.cancel(); toast(voiceOn ? 'Voice on' : 'Voice off'); };

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SR) { $('#mic').hidden = true; } else {
  const rec = new SR(); rec.lang = 'en-US'; rec.interimResults = false;
  rec.onresult = (e) => { $('#mic').classList.remove('rec'); sendChat(e.results[0][0].transcript); };
  rec.onend = rec.onerror = () => $('#mic').classList.remove('rec');
  $('#mic').onclick = () => { try { speechSynthesis.cancel(); rec.start(); $('#mic').classList.add('rec'); toast('Listening…'); } catch {} };
}

/* ---------- mood check-in ---------- */
$('#moods').innerHTML = MOODS.map(([m, e]) => `<button class="mood" data-m="${m}" aria-label="${m}">${e}</button>`).join('');
$('#moods').onclick = async (e) => {
  const b = e.target.closest('.mood'); if (!b || busy) return;
  $$('.mood').forEach((x) => x.classList.toggle('on', x === b));
  busy = true;
  try {
    const r = await api('/api/mood', { session_id: sid, mood: b.dataset.m, name });
    show('chat'); addMsg('me', `I feel ${b.dataset.m} ${b.textContent}`); const el = addMsg('bot', r.reply);
    setMode(r.mode, r.reason); if (r.mode === 'support') addBreathe();
    r.mode === 'engage' ? quickChips([['🎈 Open Play', () => show('play')], ['🌱 Teach me a word', () => sendChat('Teach me a new word')]]) : defaultChips();
    state = r.state; renderStats(); speak(r.reply);
  } catch { toast('Dora is sleepy. Try again!'); }
  busy = false;
};

/* ---------- play (quiz) ---------- */
async function loadQuiz() {
  try {
    quiz = await api(`/api/quiz?session_id=${sid}&prev=${encodeURIComponent(quiz ? quiz.id : '')}`);
  } catch { toast('Could not load a question'); return; }
  attempt = 0; locked = false; $('#qnext').hidden = true; $('#qfb').innerHTML = '&nbsp;';
  const v = quiz.visual;
  $('#qvisual').innerHTML = v.kind === 'color' ? `<div class="swatch" style="background:${v.value}"></div>` :
    v.kind === 'sentence' ? `<div class="sent"><span>${v.emoji}</span>${v.value.replace('___', '<em>&nbsp;&nbsp;&nbsp;</em>')}</div>` : v.value;
  $('#qprompt').textContent = quiz.prompt;
  $('#opts').innerHTML = '';
  quiz.options.forEach((o) => {
    const b = document.createElement('button'); b.className = 'opt clay soft press'; b.textContent = o; b.onclick = () => pick(b, o); $('#opts').append(b);
  });
  renderStats(); speak(quiz.prompt.replace(/[“”]/g, ''));
}
async function pick(btn, choice) {
  if (locked || btn.disabled) return;
  attempt++;
  try {
    const r = await api('/api/answer', { session_id: sid, item_id: quiz.id, choice, attempt });
    state = r.state; $('#qfb').textContent = r.message; speak(r.message.replace(/[“”]/g, ''));
    if (r.correct) { btn.classList.add('ok'); burst(btn); end(); }
    else { btn.classList.add('bad'); btn.disabled = true; if (r.reveal) { $$('.opt').forEach((b) => { if (b.textContent === r.answer) b.classList.add('ok'); b.disabled = true; }); end(); } }
    renderStats();
    if (r.leveled_up) setTimeout(() => levelUp(r.state), 900);
  } catch { toast('Oops, try again!'); attempt--; }
  function end() { locked = true; $$('.opt').forEach((b) => (b.disabled = true)); $('#qnext').hidden = false; }
}
$('#qnext').onclick = loadQuiz;

/* ---------- start ---------- */
$('#splashCrane').innerHTML = crane(8);
$('#nameIn').value = name;
const mascot = $('#mascot');
const mascotFallback = () => mascot.replaceWith(Object.assign(document.createElement('div'), { innerHTML: crane(8), className: 'float', style: 'width:72%;margin-bottom:10px' }));
mascot.onerror = mascotFallback;
if (mascot.complete && mascot.naturalWidth === 0) mascotFallback(); // image already failed before this script ran
async function begin() {
  const v = $('#nameIn').value.trim(); if (v) { name = v; store.set('sb_name', v); }
  show('home'); try { const r = await api(`/api/state?session_id=${sid}&name=${encodeURIComponent(name)}`); state = r.state; renderStats(); } catch {}
  if ('speechSynthesis' in window) speechSynthesis.getVoices();
}
$('#begin').onclick = begin;
$('#nameIn').addEventListener('keydown', (e) => { if (e.key === 'Enter') begin(); });
fetch('/api/health').catch(() => {}); // wakes a sleeping free-tier server while the child reads the splash
