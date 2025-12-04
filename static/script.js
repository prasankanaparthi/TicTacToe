// static/script.js — Pro UI + backend integration + confetti + sounds + winning line
document.addEventListener("DOMContentLoaded", () => {
  // --- config & state ---
  let gameId = null;
  let soundOn = true;
  const confettiCanvas = document.getElementById("confettiCanvas");
  const ctx = confettiCanvas.getContext ? confettiCanvas.getContext('2d') : null;

  const cells = Array.from(document.querySelectorAll(".cell"));
  const statusText = document.getElementById("status");
  const newGameBtn = document.getElementById("newGame");
  const resetBtn = document.getElementById("resetBtn");
  const aiModeSelect = document.getElementById("aiMode");
  const startPlayerSelect = document.getElementById("startPlayer");
  const soundToggle = document.getElementById("soundToggle");
  const scoreXEl = document.getElementById("scoreX");
  const scoreOEl = document.getElementById("scoreO");
  const winLineSvg = document.getElementById("winLineSvg");

  // Resize confetti canvas
  function resizeCanvas() {
    confettiCanvas.width = window.innerWidth;
    confettiCanvas.height = window.innerHeight;
  }
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();

  // Simple sounds (beeps) using WebAudio
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  const audioCtx = AudioCtx ? new AudioCtx() : null;
  function beep(freq=440, dur=0.08, vol=0.15){
    if (!audioCtx || !soundOn) return;
    const o = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    o.type='sine'; o.frequency.value = freq;
    g.gain.value = vol;
    o.connect(g); g.connect(audioCtx.destination);
    o.start(); g.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + dur);
    setTimeout(()=>o.stop(), dur*1000 + 20);
  }

  // SVGs for X and O (kept lightweight)
  const SVG_X = `<svg class="icon-x" viewBox="0 0 64 64"><line x1="12" y1="12" x2="52" y2="52" stroke="white" stroke-width="6" stroke-linecap="round"/><line x1="52" y1="12" x2="12" y2="52" stroke="white" stroke-width="6" stroke-linecap="round"/></svg>`;
  const SVG_O = `<svg class="icon-o" viewBox="0 0 64 64"><circle cx="32" cy="32" r="18" fill="none" stroke="white" stroke-width="6" /></svg>`;

  // helper: draw a mark into cell (with color style)
  function renderMark(cellEl, mark) {
    cellEl.innerHTML = '';
    if (!mark) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'icon';
    if (mark === 'X') {
      wrapper.innerHTML = SVG_X;
      wrapper.querySelector('svg').style.filter = "drop-shadow(0 6px 16px rgba(255,107,107,0.18))";
    } else {
      wrapper.innerHTML = SVG_O;
      wrapper.querySelector('svg').style.filter = "drop-shadow(0 8px 18px rgba(79,195,247,0.16))";
    }
    cellEl.appendChild(wrapper);
  }

  // --- UI helpers ---
  function setStatus(text){ statusText.textContent = text; }
  function setScores(x,y){ scoreXEl.textContent = x; scoreOEl.textContent = y; }

  // draw winning line between two cell centers (use SVG coords)
  function animateWinLine(aIndex, bIndex) {
    const board = document.querySelector('.board');
    const r = board.getBoundingClientRect();
    const a = cells[aIndex].getBoundingClientRect();
    const b = cells[bIndex].getBoundingClientRect();
    // center coords
    const ax = (a.left + a.right)/2 - r.left;
    const ay = (a.top + a.bottom)/2 - r.top;
    const bx = (b.left + b.right)/2 - r.left;
    const by = (b.top + b.bottom)/2 - r.top;
    winLineSvg.setAttribute('x1', ax);
    winLineSvg.setAttribute('y1', ay);
    winLineSvg.setAttribute('x2', ax);
    winLineSvg.setAttribute('y2', ay);
    winLineSvg.style.opacity = 1;
    winLineSvg.style.transition = 'opacity .25s linear';
    // animate endpoint
    setTimeout(()=>{
      winLineSvg.setAttribute('x2', bx);
      winLineSvg.setAttribute('y2', by);
      // trigger dash animation
      winLineSvg.style.opacity = 1;
      winLineSvg.style.strokeDashoffset = 0;
      winLineSvg.style.transition = 'stroke-dashoffset 700ms cubic-bezier(.2,.9,.2,1), x2 700ms';
    }, 20);
    // fade after a while
    setTimeout(()=>{ winLineSvg.style.opacity = 0; winLineSvg.style.transition = 'opacity 600ms'; }, 1800);
  }

  // Confetti: small particle system (lightweight)
  function launchConfetti() {
    if (!ctx) return;
    const W = confettiCanvas.width, H = confettiCanvas.height;
    const pieces = [];
    const colors = ['#7c5cff','#4be1a2','#ff6b6b','#4fc3f7','#ffd166'];
    const count = Math.min(120, Math.floor(W/8));
    for (let i=0;i<count;i++){
      pieces.push({
        x: Math.random()*W,
        y: -20 - Math.random()*H*0.2,
        vx: (Math.random()-0.5)*6,
        vy: 2 + Math.random()*6,
        s: 6 + Math.random()*8,
        c: colors[Math.floor(Math.random()*colors.length)],
        r: Math.random()*360,
        vr: (Math.random()-0.5)*8
      });
    }
    let t = 0;
    function frame(){
      t++;
      ctx.clearRect(0,0,W,H);
      for (const p of pieces){
        p.x += p.vx;
        p.y += p.vy;
        p.r += p.vr;
        ctx.save();
        ctx.translate(p.x,p.y);
        ctx.rotate(p.r*Math.PI/180);
        ctx.fillStyle = p.c;
        ctx.fillRect(-p.s/2, -p.s/2, p.s, p.s);
        ctx.restore();
      }
      if (t<220){
        requestAnimationFrame(frame);
      } else {
        ctx.clearRect(0,0,W,H);
      }
    }
    requestAnimationFrame(frame);
  }

  // --- backend calls & game logic integration ---
  async function createNewGame(auto=false){
    try{
      const body = { starting_player: startPlayerSelect.value, ai_mode: aiModeSelect.value };
      const res = await fetch('/api/new', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Create failed');
      gameId = data.game_id;
      updateFromState(data.state);
      if (!auto) beep(660,0.06,0.08);
      // if AI starts after new game
      if (startPlayerSelect.value === 'O') await requestAiMove();
    }catch(err){ console.error(err); setStatus('Could not create game'); }
  }

  async function postMove(index){
    if (!gameId){ setStatus('Press New Game'); return; }
    try{
      const res = await fetch(`/api/move/${gameId}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({index})});
      const data = await res.json();
      if (!res.ok){ setStatus(data.error || 'Move rejected'); return; }
      updateFromState(data.state);
      beep(880,0.06,0.04);
      if (!data.state.winner) await requestAiMove();
    }catch(err){ console.error(err); setStatus('Error'); }
  }

  async function requestAiMove(){
    if (!gameId) return;
    try{
      const res = await fetch(`/api/ai_move/${gameId}`, {method:'POST'});
      const data = await res.json();
      if (!res.ok){ if (data.state) updateFromState(data.state); return; }
      updateFromState(data.state);
      beep(520,0.08,0.06);
    }catch(err){ console.error(err); }
  }

  async function resetBoard(){
    if (!gameId){ await createNewGame(); return; }
    try{
      const res = await fetch(`/api/reset/${gameId}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({starting_player:startPlayerSelect.value})});
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Reset failed');
      updateFromState(data.state);
      if (startPlayerSelect.value === 'O') await requestAiMove();
    }catch(err){ console.error(err); setStatus('Reset failed'); }
  }

  // Update UI from state from server
  function updateFromState(state){
    // board is array of '', 'X', 'O'
    state.board.forEach((v,i) => { renderMark(cells[i], v); });
    // scores: count X and O wins from history? server doesn't track global scoreboard.
    // We'll count existing wins in DOM — better: maintain scoreboard separately — for now leave as-is.
    setStatus(state.winner ? (state.winner === 'Tie' ? "It's a tie!" : `${state.winner} wins!`) : `Player ${state.current_player}'s turn`);
    // animate winner if present
    if (state.winner && state.winner !== 'Tie') {
      // find winning triple from board
      const triple = findWinningTriple(state.board);
      if (triple) {
        // animate line between first and last cells in triple
        animateWinLine(triple[0], triple[2]);
      }
      // sound + confetti
      if (soundOn) beep(320,0.16,0.12);
      launchConfetti();
      // update scoreboard locally (increment)
      if (state.winner === 'X') scoreXEl.textContent = Number(scoreXEl.textContent || 0) + 1;
      if (state.winner === 'O') scoreOEl.textContent = Number(scoreOEl.textContent || 0) + 1;
    }
  }

  // Find which triple is winning (board has 'X'/'O')
  function findWinningTriple(b){
    const lines = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
    for (const l of lines){
      const [a,b1,c] = l;
      if (b[a] && b[a] === b[b1] && b[a] === b[c]) return l;
    }
    return null;
  }

  // Attach click & keyboard handlers for cells
  cells.forEach((cell, idx) => {
    cell.addEventListener('click', ()=> {
      if (cell.textContent.trim() !== '') return;
      postMove(idx);
    });
    // keyboard support: Enter to click; Arrow keys to move focus
    cell.addEventListener('keydown', (e) => {
      const key = e.key;
      if (key === 'Enter' || key === ' ') { e.preventDefault(); cell.click(); }
      const col = idx % 3, row = Math.floor(idx / 3);
      if (key === 'ArrowRight') focusCell((row*3)+((col+1)%3));
      if (key === 'ArrowLeft') focusCell((row*3)+((col+2)%3));
      if (key === 'ArrowDown') focusCell(((row+1)%3)*3 + col);
      if (key === 'ArrowUp') focusCell(((row+2)%3)*3 + col);
    });
  });

  function focusCell(i){ cells[i].focus(); }

  newGameBtn.addEventListener('click', ()=>createNewGame(false));
  resetBtn.addEventListener('click', ()=>resetBoard());

  soundToggle.addEventListener('click', ()=> {
    soundOn = !soundOn;
    soundToggle.setAttribute('aria-pressed', String(soundOn));
    soundToggle.querySelector('.icon-sound').style.fill = soundOn ? 'var(--accent)' : 'var(--muted)';
  });

  // helper: simple renderMark wrapper for convenience
  function renderMark(cellEl, mark){
    if (!mark) { cellEl.innerHTML = ''; return; }
    const svg = mark === 'X' ? SVG_X : SVG_O;
    cellEl.innerHTML = svg;
    // color tweak
    const svgEl = cellEl.querySelector('svg');
    if (mark === 'X') svgEl.style.stroke = 'white';
    else svgEl.style.stroke = 'white';
  }

  // Expose minimal debugging to console
  window.tt = { createNewGame, postMove, requestAiMove, resetBoard };

  // Auto-create a new game on load
  createNewGame(true);
});
