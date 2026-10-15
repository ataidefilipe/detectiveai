/**
 * Detective AI — Jazz Noir Audio Controller
 * Gerencia a reprodução da trilha sonora ambiente, controles de volume e persistência sincronizada.
 */

(function () {
  const STORAGE_KEY_VOL = 'detective_jazz_volume';
  const STORAGE_KEY_MUTED = 'detective_jazz_muted';
  const AUDIO_SRC = '/static/assets/audio/jazz-noir.mp3';

  let audioElement = null;
  let isPlaying = false;

  function initAudioPlayer() {
    // 1. Criar ou referenciar elemento global de áudio
    audioElement = document.getElementById('jazz-audio-element');
    if (!audioElement) {
      audioElement = document.createElement('audio');
      audioElement.id = 'jazz-audio-element';
      audioElement.src = AUDIO_SRC;
      audioElement.loop = true;
      audioElement.preload = 'metadata';
      document.body.appendChild(audioElement);
    }

    // 2. Recuperar preferências salvas
    const savedVol = localStorage.getItem(STORAGE_KEY_VOL);
    const savedMuted = localStorage.getItem(STORAGE_KEY_MUTED);

    const initialVol = savedVol !== null ? parseFloat(savedVol) : 0.4;
    const initialMuted = savedMuted === 'true';

    audioElement.volume = initialVol;
    audioElement.muted = initialMuted;

    // 3. Renderizar slots automáticos e vincular widgets
    document.querySelectorAll('.jazz-player-slot').forEach(slot => {
      slot.innerHTML = getWidgetMarkup();
    });
    bindWidgets();

    // 4. Ouvintes de eventos do elemento de áudio
    audioElement.addEventListener('play', () => updatePlayState(true));
    audioElement.addEventListener('pause', () => updatePlayState(false));
    audioElement.addEventListener('ended', () => updatePlayState(false));

    updateMuteState(initialMuted);
    updateVolumeState(initialVol);
  }

  function bindWidgets() {
    document.querySelectorAll('.jazz-btn-play').forEach(btn => {
      btn.onclick = togglePlay;
    });

    document.querySelectorAll('.jazz-btn-mute').forEach(btn => {
      btn.onclick = () => toggleMute(!audioElement.muted);
    });

    document.querySelectorAll('.jazz-volume-slider').forEach(slider => {
      slider.oninput = (e) => {
        const val = parseFloat(e.target.value) / 100;
        setVolume(val);
      };
    });
  }

  function togglePlay() {
    if (!audioElement) return;

    if (isPlaying) {
      audioElement.pause();
    } else {
      audioElement.play().then(() => {
        updatePlayState(true);
      }).catch((err) => {
        console.warn('Autoplay bloqueado pelo navegador ou erro de áudio:', err);
      });
    }
  }

  function setVolume(val) {
    if (!audioElement) return;
    audioElement.volume = val;
    localStorage.setItem(STORAGE_KEY_VOL, val);
    updateVolumeState(val);
    if (audioElement.muted && val > 0) {
      toggleMute(false);
    }
  }

  function toggleMute(muted) {
    if (!audioElement) return;
    audioElement.muted = muted;
    localStorage.setItem(STORAGE_KEY_MUTED, muted);
    updateMuteState(muted);
  }

  function updateMuteState(isMuted) {
    document.querySelectorAll('.jazz-btn-mute').forEach(btn => {
      btn.textContent = isMuted ? '🔇' : '🔊';
      btn.title = isMuted ? 'Unmute Jazz' : 'Mute Jazz';
    });
  }

  function updateVolumeState(val) {
    document.querySelectorAll('.jazz-volume-slider').forEach(slider => {
      slider.value = Math.round(val * 100);
    });
  }

  function updatePlayState(playing) {
    isPlaying = playing;
    document.querySelectorAll('.jazz-btn-play').forEach(btn => {
      btn.textContent = playing ? '⏸' : '▶';
      btn.title = playing ? 'Pause Soundtrack' : 'Play Jazz Noir';
    });

    document.querySelectorAll('.jazz-sound-waves').forEach(wave => {
      if (playing) {
        wave.classList.add('playing');
      } else {
        wave.classList.remove('playing');
      }
    });

    document.querySelectorAll('.jazz-status').forEach(status => {
      status.textContent = playing ? 'Playing' : 'Paused';
    });
  }

  // Gera o HTML do widget para injeção rápida
  function getWidgetMarkup() {
    const isMuted = audioElement ? audioElement.muted : false;
    const vol = audioElement ? Math.round(audioElement.volume * 100) : 40;
    return `
      <div class="jazz-player-widget">
        <button class="jazz-btn-play" title="Play Jazz Noir">▶</button>
        <div class="jazz-info">
          <div style="display:flex;align-items:center;gap:4px;">
            <span class="jazz-title">JAZZ NOIR</span>
            <div class="jazz-sound-waves"><span></span><span></span><span></span></div>
          </div>
          <span class="jazz-status">Paused</span>
        </div>
        <input type="range" class="jazz-volume-slider" min="0" max="100" value="${vol}" title="Volume">
        <button class="jazz-btn-mute" title="Mute/Unmute">${isMuted ? '🔇' : '🔊'}</button>
      </div>
    `;
  }

  // Inicializar quando o DOM estiver pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAudioPlayer);
  } else {
    initAudioPlayer();
  }

  // Expor API global
  window.DetectiveAudio = {
    togglePlay,
    toggleMute,
    setVolume,
    getWidgetMarkup,
    bindWidgets,
    getElement: () => audioElement
  };
})();
