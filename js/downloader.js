/**
 * StreamRip Core - Extraction & Download Controller
 */

async function pollJob(jobId, onDone) {
  const elProgress = document.getElementById('progress-bar');
  try {
    const res = await fetch(`/api/job/${jobId}`);
    if (res.status === 404) {
      if (AppState.pollTimer) {
        clearInterval(AppState.pollTimer);
        AppState.pollTimer = null;
      }
      appendLog('Pipeline ended: job expired on the backend.', 'entry-danger');
      onDone(1);
      return true;
    }
    const data = await res.json();

    (data.logs || []).forEach((l) => appendLog(l.msg, tagToClass(l.tag)));

    if (typeof data.percent === 'number' && elProgress) {
      elProgress.style.width = `${data.percent}%`;
    }

    if (data.done) {
      if (AppState.pollTimer) {
        clearInterval(AppState.pollTimer);
        AppState.pollTimer = null;
      }
      onDone(data.exit_code);
      return true;
    }
  } catch (err) {
    appendLog(`Poll error: ${err}`, 'entry-danger');
  }
  return false;
}

async function handleDownloadClick() {
  const elUrl = document.getElementById('target-url');
  const elDest = document.getElementById('dest-path');
  const elDownload = document.getElementById('btn-download');
  const elStatus = document.getElementById('status-label');
  const elProgress = document.getElementById('progress-bar');
  const elSelectQuality = document.getElementById('select-quality');
  const elSelectCaption = document.getElementById('select-caption');
  const elChkTranscript = document.getElementById('chk-transcript');

  const elPip = document.getElementById('status-pip');

  const rawUrl = elUrl ? elUrl.value.trim() : '';
  if (!rawUrl) {
    appendLog('Error: Source URL cannot be empty.', 'entry-danger');
    if (elUrl) elUrl.focus();
    return;
  }

  const isYtMode = AppState.mode === 'youtube';
  const looksYt = /^(https?:\/\/)?(www\.|music\.|m\.)?(youtube\.com|youtu\.be)\//i.test(rawUrl);
  const looksSp = /^(https?:\/\/)?(open\.spotify\.com)\//i.test(rawUrl);
  if ((isYtMode && !looksYt) || (!isYtMode && !looksSp)) {
    appendLog(isYtMode ? 'Error: that link is not a YouTube URL. Switch to Spotify mode for Spotify links.' : 'Error: that link is not a Spotify URL. Switch to YouTube mode for YouTube links.', 'entry-danger');
    if (elUrl) elUrl.focus();
    return;
  }

  // Abort if already running
  if (AppState.isProcessing) {
    if (AppState.activeJob) {
      await fetch(`/api/job/${AppState.activeJob}/abort`, { method: 'POST' });
      appendLog('Abort requested.', 'entry-blue');
    }
    return;
  }

  AppState.isProcessing = true;
  if (elDownload) {
    elDownload.disabled = false;
    elDownload.innerHTML = 'Cancel Extraction';
    elDownload.classList.add('is-cancel');
  }
  if (elStatus) elStatus.textContent = 'Processing';
  if (elPip) {
    elPip.classList.remove('is-fail');
    elPip.classList.add('is-busy');
  }
  if (elProgress) elProgress.style.width = '0%';

  appendLog(`Target verified: ${rawUrl}`);

  try {
    const elSelectFormat = document.getElementById('select-format');
    const elSelectBitrate = document.getElementById('select-bitrate');
    const elChkLyrics = document.getElementById('chk-lyrics');
    const elSelectFileFormat = document.getElementById('select-file-format');
    const elSelectLang = document.getElementById('select-transcript-lang');
    const fileFormatText = elSelectFileFormat ? elSelectFileFormat.options[elSelectFileFormat.selectedIndex]?.text : 'Match Source (no conversion)';
    const qualityText = elSelectQuality ? elSelectQuality.options[elSelectQuality.selectedIndex]?.text : 'Best Available (Source)';

    const payload = {
      url: rawUrl,
      mode: AppState.mode,
      out_dir: elDest ? elDest.value.trim() : '',
      yt_stream: elSelectQuality ? elSelectQuality.options[elSelectQuality.selectedIndex]?.text : 'Best Available (Source)',
      yt_caption_env: elSelectCaption ? elSelectCaption.options[elSelectCaption.selectedIndex]?.text : 'SubRip Subtitle (.srt)',
      yt_capture_subs: elChkTranscript ? elChkTranscript.checked : false,
      yt_transcript_only: false,
      yt_lang: elSelectLang ? elSelectLang.options[elSelectLang.selectedIndex]?.text : 'English',
      yt_file_format: fileFormatText,
      yt_audio_quality: /audio/i.test(fileFormatText || '') ? qualityText : 'Best Available',
      sp_stream: elSelectFormat ? elSelectFormat.options[elSelectFormat.selectedIndex]?.text : 'MP3 Audio (.mp3)',
      sp_bitrate: elSelectBitrate ? elSelectBitrate.options[elSelectBitrate.selectedIndex]?.text : 'Auto (Best Match)',
      sp_generate_lrc: elChkLyrics ? elChkLyrics.checked : false,
    };

    const res = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (data.error) throw new Error(data.error);

    AppState.activeJob = data.job_id;
    appendLog(`Pipeline started (job ${AppState.activeJob}).`, 'entry-blue');

    if (AppState.pollTimer) {
      clearInterval(AppState.pollTimer);
      AppState.pollTimer = null;
    }
    AppState.pollTimer = setInterval(async () => {
      await pollJob(AppState.activeJob, (code) => {
        AppState.isProcessing = false;
        AppState.activeJob = null;
        if (elDownload) {
          elDownload.innerHTML = 'Start Extraction';
          elDownload.classList.remove('is-cancel');
        }
        if (elStatus) elStatus.textContent = code === 0 ? 'Standby' : 'Failed';
        if (elPip) {
          elPip.classList.remove('is-busy');
          elPip.classList.toggle('is-fail', code !== 0);
        }
        if (elProgress && code === 0) elProgress.style.width = '100%';
        if (code === 0) appendLog('Execution finished.', 'entry-success');
        else appendLog(`Pipeline halted with exit code ${code}.`, 'entry-danger');
      });
    }, 400);
  } catch (err) {
    appendLog(`Error: ${err.message}`, 'entry-danger');
    AppState.isProcessing = false;
    if (elDownload) {
      elDownload.innerHTML = 'Start Extraction';
      elDownload.classList.remove('is-cancel');
    }
    if (elStatus) elStatus.textContent = 'Standby';
    if (elPip) elPip.classList.remove('is-busy');
  }
}
