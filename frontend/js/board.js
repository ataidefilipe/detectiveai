/**
 * ═════════════════════════════════════════════════════════════════════
 * DETECTIVE AI — WHITEBOARD ENGINE (MURAL DE DETETIVE)
 * Native HTML5 Pointer Events + SVG Bézier Red Strings
 * ═════════════════════════════════════════════════════════════════════
 */

const DetectiveBoard = (() => {
  let boardState = {
    nodes: [],
    connections: [],
    stickers: []
  };

  let activeDrag = null;
  let activePinId = null;
  let saveTimer = null;

  // ── Inicialização & Carregamento ──────────────────────────────
  async function openBoard() {
    if (!state.sessionId) {
      toast('⚠️', 'No active investigation selected.', 'warn');
      return;
    }

    showScreen('screen-board');
    updateSaveStatus('Loading whiteboard…', '');

    try {
      const data = await api(`/sessions/${state.sessionId}/board`);
      boardState = data.board_data || { nodes: [], connections: [], stickers: [] };
      renderAll();
      updateSaveStatus('🟢 Saved', 'saved');
    } catch (e) {
      toast('Whiteboard Error', e.message, 'lie');
      updateSaveStatus('🔴 Error syncing', 'error');
    }
  }

  function updateSaveStatus(text, statusClass) {
    const el = document.getElementById('board-save-status');
    if (!el) return;
    el.textContent = text;
    el.className = 'board-save-status ' + (statusClass || '');
  }

  // ── Renderização Completa ─────────────────────────────────────
  function renderAll() {
    renderItems();
    renderStrings();
  }

  // Renderiza cards e post-its
  function renderItems() {
    const canvas = document.getElementById('board-canvas');
    if (!canvas) return;

    // Remove nós e stickers antigos mantendo a camada SVG
    const svgLayer = document.getElementById('board-svg-layer');
    canvas.querySelectorAll('.board-item').forEach(el => el.remove());

    // 1. Suspeitos e Evidências (Nodes)
    (boardState.nodes || []).forEach(node => {
      const el = document.createElement('div');
      el.className = 'board-item';
      el.id = `item-${node.id}`;
      el.style.left = `${node.x}px`;
      el.style.top = `${node.y}px`;

      const isSuspect = node.type === 'suspect';
      const defaultImg = isSuspect
        ? '/static/assets/templates/suspect-template.svg'
        : '/static/assets/templates/evidence-template.svg';
      const imgSrc = node.image_url || defaultImg;

      if (isSuspect) {
        el.innerHTML = `
          <div class="board-pin" title="Click to connect red string" data-pin-id="${node.id}"></div>
          <div class="board-suspect-card">
            <div class="board-suspect-photo">
              <img src="${imgSrc}" alt="${node.title}" onerror="this.src='/static/assets/templates/suspect-template.svg'" />
            </div>
            <div class="board-suspect-info">
              <div class="board-suspect-name">${node.title}</div>
              <div class="board-suspect-role">${node.subtitle || 'Suspect'}</div>
            </div>
          </div>
        `;
      } else {
        el.innerHTML = `
          <div class="board-pin" title="Click to connect red string" data-pin-id="${node.id}"></div>
          <div class="board-evidence-card">
            <div class="board-evidence-thumb">
              <img src="${imgSrc}" alt="${node.title}" onerror="this.src='/static/assets/templates/evidence-template.svg'" />
            </div>
            <div class="board-evidence-code">${node.subtitle || 'EV'}</div>
            <div class="board-evidence-title">${node.title}</div>
          </div>
        `;
      }

      setupDrag(el, node.id, false);
      setupPin(el, node.id);
      canvas.appendChild(el);
    });

    // 2. Stickers / Post-its
    (boardState.stickers || []).forEach(sticker => {
      const el = createStickyElement(sticker);
      canvas.appendChild(el);
    });
  }

  function createStickyElement(sticker) {
    const el = document.createElement('div');
    el.className = 'board-item';
    el.id = `item-${sticker.id}`;
    el.style.left = `${sticker.x}px`;
    el.style.top = `${sticker.y}px`;

    const color = sticker.color || 'yellow';
    el.innerHTML = `
      <div class="board-pin" title="Click to connect red string" data-pin-id="${sticker.id}"></div>
      <div class="board-sticky-note ${color}" id="note-${sticker.id}">
        <div class="sticky-top-bar">
          <div class="sticky-colors">
            <span class="sticky-color-dot yellow" title="Yellow" onclick="DetectiveBoard.setStickyColor('${sticker.id}', 'yellow')"></span>
            <span class="sticky-color-dot pink" title="Alert" onclick="DetectiveBoard.setStickyColor('${sticker.id}', 'pink')"></span>
            <span class="sticky-color-dot blue" title="Clue" onclick="DetectiveBoard.setStickyColor('${sticker.id}', 'blue')"></span>
          </div>
          <button class="sticky-delete-btn" title="Delete note" onclick="DetectiveBoard.deleteStickyNote('${sticker.id}')">✕</button>
        </div>
        <textarea class="sticky-textarea" placeholder="Write your deduction…" oninput="DetectiveBoard.onStickyTextChange('${sticker.id}', this.value)">${escapeHtml(sticker.text || '')}</textarea>
      </div>
    `;

    setupDrag(el, sticker.id, true);
    setupPin(el, sticker.id);
    return el;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // ── Drag & Drop com Pointer Events ────────────────────────────
  function setupDrag(element, id, isSticker) {
    element.addEventListener('pointerdown', (e) => {
      // Ignora clique em alfinete, textarea ou botões de cor
      if (e.target.closest('.board-pin') || e.target.closest('textarea') || e.target.closest('button') || e.target.closest('.sticky-color-dot')) {
        return;
      }

      element.setPointerCapture(e.pointerId);
      element.classList.add('dragging');

      const startLeft = parseFloat(element.style.left) || 0;
      const startTop = parseFloat(element.style.top) || 0;

      activeDrag = {
        id,
        element,
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        origLeft: startLeft,
        origTop: startTop,
        isSticker
      };
    });

    element.addEventListener('pointermove', (e) => {
      if (!activeDrag || activeDrag.id !== id) return;

      const deltaX = e.clientX - activeDrag.startX;
      const deltaY = e.clientY - activeDrag.startY;

      const newLeft = Math.max(10, Math.min(2180, activeDrag.origLeft + deltaX));
      const newTop  = Math.max(10, Math.min(1400, activeDrag.origTop + deltaY));

      element.style.left = `${newLeft}px`;
      element.style.top  = `${newTop}px`;

      // Atualiza coordenadas no estado em memória
      if (activeDrag.isSticker) {
        const item = boardState.stickers.find(s => s.id === id);
        if (item) { item.x = newLeft; item.y = newTop; }
      } else {
        const item = boardState.nodes.find(n => n.id === id);
        if (item) { item.x = newLeft; item.y = newTop; }
      }

      // Redesenha os fios em tempo real com requestAnimationFrame
      requestAnimationFrame(renderStrings);
    });

    const endDrag = (e) => {
      if (!activeDrag || activeDrag.id !== id) return;
      element.classList.remove('dragging');
      try { element.releasePointerCapture(e.pointerId); } catch (err) {}
      activeDrag = null;
      saveBoardDebounced();
    };

    element.addEventListener('pointerup', endDrag);
    element.addEventListener('pointercancel', endDrag);
  }

  // ── Conexão de Fios Vermelhos (Red Strings) ───────────────────
  function setupPin(element, id) {
    const pin = element.querySelector('.board-pin');
    if (!pin) return;

    pin.addEventListener('click', (e) => {
      e.stopPropagation();

      if (!activePinId) {
        // Seleciona primeiro ponto
        activePinId = id;
        pin.classList.add('pin-selected');
        toast('🧶 String', 'Select the second pin to link the connection.', 'hint', 4000);
      } else if (activePinId === id) {
        // Clicou no mesmo alfinete: cancela seleção
        activePinId = null;
        pin.classList.remove('pin-selected');
      } else {
        // Clicou em outro alfinete: liga ou desliga a conexão
        toggleConnection(activePinId, id);
        clearPinSelection();
      }
    });
  }

  function clearPinSelection() {
    activePinId = null;
    document.querySelectorAll('.board-pin').forEach(p => p.classList.remove('pin-selected'));
  }

  function toggleConnection(fromId, toId) {
    // Verifica se já existe conexão direta ou inversa
    const existingIdx = boardState.connections.findIndex(
      c => (c.from_id === fromId && c.to_id === toId) || (c.from_id === toId && c.to_id === fromId)
    );

    if (existingIdx >= 0) {
      boardState.connections.splice(existingIdx, 1);
      toast('✂️ String Cut', 'Connection removed.', 'hint', 2000);
    } else {
      boardState.connections.push({
        id: `conn-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
        from_id: fromId,
        to_id: toId
      });
      toast('🧶 String Connected', 'Connection linked.', 'ok', 2000);
    }

    renderStrings();
    saveBoardDebounced();
  }

  // ── Renderização das Curvas de Bézier (SVG) ───────────────────
  function renderStrings() {
    const svgLayer = document.getElementById('board-svg-layer');
    if (!svgLayer) return;

    svgLayer.innerHTML = '';

    (boardState.connections || []).forEach(conn => {
      const elFrom = document.getElementById(`item-${conn.from_id}`);
      const elTo   = document.getElementById(`item-${conn.to_id}`);

      if (!elFrom || !elTo) return;

      const p1 = getPinCenter(elFrom);
      const p2 = getPinCenter(elTo);

      // Curva sutil de barbante solto (Bézier cúbica com caimento gravítico)
      const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
      const sag = Math.min(60, Math.max(15, dist * 0.12));

      const cx1 = p1.x;
      const cy1 = p1.y + sag;
      const cx2 = p2.x;
      const cy2 = p2.y + sag;

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M ${p1.x} ${p1.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${p2.x} ${p2.y}`);
      path.setAttribute('class', 'red-string-path');
      path.setAttribute('title', 'Click to cut this string');

      path.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleConnection(conn.from_id, conn.to_id);
      });

      svgLayer.appendChild(path);
    });
  }

  function getPinCenter(itemEl) {
    const pin = itemEl.querySelector('.board-pin');
    const x = parseFloat(itemEl.style.left) || 0;
    const y = parseFloat(itemEl.style.top) || 0;
    const width = itemEl.offsetWidth || 200;

    return {
      x: x + (width / 2),
      y: y + 2 // Centro vertical da cabeça do alfinete
    };
  }

  // ── Ações de Post-it ──────────────────────────────────────────
  function addStickyNote(color = 'yellow') {
    const viewport = document.getElementById('board-viewport');
    const scrollLeft = viewport ? viewport.scrollLeft : 300;
    const scrollTop  = viewport ? viewport.scrollTop : 200;

    const newNote = {
      id: `sticker-${Date.now()}`,
      text: '',
      color: color,
      x: scrollLeft + 120 + Math.floor(Math.random() * 60),
      y: scrollTop + 100 + Math.floor(Math.random() * 60)
    };

    boardState.stickers.push(newNote);
    const canvas = document.getElementById('board-canvas');
    if (canvas) {
      canvas.appendChild(createStickyElement(newNote));
    }
    saveBoardDebounced();
  }

  function deleteStickyNote(id) {
    boardState.stickers = boardState.stickers.filter(s => s.id !== id);
    // Remove conexões que envolviam esse sticker
    boardState.connections = boardState.connections.filter(c => c.from_id !== id && c.to_id !== id);

    const el = document.getElementById(`item-${id}`);
    if (el) el.remove();

    renderStrings();
    saveBoardDebounced();
    toast('🗑️ Note Removed', 'Sticky note deleted.', 'hint', 2000);
  }

  function setStickyColor(id, color) {
    const note = boardState.stickers.find(s => s.id === id);
    if (!note) return;
    note.color = color;

    const noteEl = document.getElementById(`note-${id}`);
    if (noteEl) {
      noteEl.className = `board-sticky-note ${color}`;
    }
    saveBoardDebounced();
  }

  function onStickyTextChange(id, text) {
    const note = boardState.stickers.find(s => s.id === id);
    if (note) {
      note.text = text;
      saveBoardDebounced();
    }
  }

  function clearConnections() {
    if (!boardState.connections.length) {
      toast('ℹ️ Whiteboard', 'No string connections to remove.', 'hint', 2000);
      return;
    }
    boardState.connections = [];
    renderStrings();
    saveBoardDebounced();
    toast('✂️ Strings Cleared', 'All board connections have been cleared.', 'ok', 3000);
  }

  // ── Persistência com Debounce ─────────────────────────────────
  function saveBoardDebounced() {
    updateSaveStatus('🟡 Saving…', 'saving');
    clearTimeout(saveTimer);

    saveTimer = setTimeout(async () => {
      try {
        await api(`/sessions/${state.sessionId}/board`, {
          method: 'PUT',
          body: JSON.stringify({ board_data: boardState })
        });
        updateSaveStatus('🟢 Saved', 'saved');
      } catch (e) {
        updateSaveStatus('🔴 Error saving', 'error');
        toast('Save Error', e.message, 'lie');
      }
    }, 800);
  }

  return {
    openBoard,
    addStickyNote,
    deleteStickyNote,
    setStickyColor,
    onStickyTextChange,
    clearConnections,
    clearPinSelection
  };
})();
