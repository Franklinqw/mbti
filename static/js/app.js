/* 本色：原生 JavaScript 单页流程，无前端依赖。 */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const storageKey = () => 'inner-you-progress-v2-' + (Account.user?.id || 'guest');
  const labels = {simple: '简版测试', full: '完整版测试'};
  const dimensions = {EI: ['外向 E', '内向 I'], SN: ['实感 S', '直觉 N'], TF: ['思考 T', '情感 F'], JP: ['判断 J', '知觉 P']};
  let attemptId = null, identity = null;
  let mode = 'simple', questions = [], answers = [], current = 0, busy = false, report = null, noticeTimer;
  const storage = {
    read() { try { return JSON.parse(localStorage.getItem(storageKey())); } catch { return null; } },
    write(value) { try { localStorage.setItem(storageKey(), JSON.stringify(value)); return true; } catch { return false; } },
    clear() { try { localStorage.removeItem(storageKey()); } catch { /* 浏览器可能禁用了存储。 */ } }
  };
  function notify(message) {
    $('status-message').textContent = message;
    $('status-message').hidden = false;
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => { $('status-message').hidden = true; }, 6000);
  }
  function show(name) {
    for (const screen of document.querySelectorAll('.screen')) screen.hidden = screen.id !== name + '-screen';
    window.scrollTo({top: 0, behavior: 'instant'});
    const title = $(name + '-screen').querySelector('h1');
    if (title) title.focus({preventScroll: true});
  }
  function readProgress() {
    const saved = storage.read();
    if (!Account.user || !saved || typeof saved.attemptId !== 'string' || !Object.hasOwn(labels, saved.mode) || !Array.isArray(saved.answers)) return null;
    const total = saved.mode === 'full' ? 60 : 20;
    if (saved.answers.length !== total || !Number.isInteger(saved.current) || saved.current < 0 || saved.current >= total) return null;
    if (!saved.answers.every(a => a === null || a === 'A' || a === 'B')) return null;
    return saved;
  }
  function refreshResume() {
    const saved = readProgress();
    $('resume-banner').hidden = !saved;
    if (saved) $('resume-text').textContent = `${labels[saved.mode]} · 已完成 ${saved.answers.filter(Boolean).length} / ${saved.answers.length} 题`;
  }
  function save() {
    const ok = storage.write({mode, answers, current, attemptId});
    $('saved-status').textContent = ok ? '✓ 进度已保存在本机' : '当前浏览器未允许保存进度';
  }
  async function request(url, options) {
    return (await Account.api(url, options)).data;
  }
  async function start(selectedMode, saved = null) {
    await Account.ready;
    if (!Account.requireLogin('#choose') || busy) return;
    const owner = Account.user.id;
    busy = true;
    document.querySelectorAll('[data-mode], #resume').forEach(button => button.disabled = true);
    try {
      const data = saved ? await request('/api/attempts/' + saved.attemptId) : await request('/api/attempts', {method:'POST', body:JSON.stringify({mode:selectedMode})});
      if (Account.user?.id !== owner) throw new Error('登录状态已变化，请重新开始');
      attemptId = data.attemptId;
      mode = selectedMode;
      questions = data.questions;
      // 交错展示各维度，保留 API 原始题号用于计分。
      const groups = Object.keys(dimensions).map(dim => questions.filter(q => q.dimension === dim));
      questions = groups[0].flatMap((_, index) => groups.map(group => group[index]));
      answers = saved ? saved.answers.slice() : Array(questions.length).fill(null);
      current = saved ? saved.current : 0;
      report = null;
      $('test-mode').textContent = labels[mode];
      location.hash = 'test';
      show('test');
      renderQuestion();
      save();
    } catch (error) { notify('题目加载失败，请重试：' + error.message); }
    finally {
      busy = false;
      document.querySelectorAll('[data-mode], #resume').forEach(button => button.disabled = false);
    }
  }
  function renderQuestion() {
    const q = questions[current], count = answers.filter(Boolean).length;
    const percent = Math.round(count / questions.length * 100);
    $('progress-text').textContent = `已完成 ${count} / ${questions.length} 题`;
    $('progress-percent').textContent = percent + '%';
    $('progress-fill').style.width = percent + '%';
    $('progress-track').setAttribute('aria-valuenow', percent);
    $('question-number').textContent = `QUESTION ${String(current + 1).padStart(2, '0')} / ${questions.length}`;
    $('question-text').textContent = q.text;
    $('options-list').replaceChildren();
    q.options.forEach(option => {
      const button = document.createElement('button');
      button.className = 'option-item';
      button.setAttribute('aria-pressed', String(answers[current] === option.key));
      const key = document.createElement('span'); key.className = 'option-key'; key.textContent = option.key;
      const text = document.createElement('span'); text.textContent = option.text;
      button.append(key, text);
      button.addEventListener('click', () => {
        if (busy) return;
        answers[current] = option.key;
        document.querySelectorAll('.option-item').forEach(el => el.setAttribute('aria-pressed', String(el === button)));
        $('next').disabled = false;
        save();
        const completed = answers.filter(Boolean).length;
        $('progress-text').textContent = `已完成 ${completed} / ${questions.length} 题`;
        const pct = Math.round(completed / questions.length * 100);
        $('progress-percent').textContent = pct + '%';
        $('progress-fill').style.width = pct + '%';
        $('progress-track').setAttribute('aria-valuenow', pct);
      });
      $('options-list').append(button);
    });
    $('previous').disabled = current === 0;
    $('next').disabled = !answers[current];
    $('next').textContent = current === questions.length - 1 ? '查看我的结果 ↗' : '下一题 →';
    $('question-text').focus({preventScroll: true});
  }
  async function submit() {
    if (busy) return;
    const owner = Account.user?.id;
    const missing = answers.findIndex(answer => !answer);
    if (missing !== -1) { current = missing; renderQuestion(); notify('请先完成这道题目。'); return; }
    busy = true;
    $('next').disabled = true;
    $('previous').disabled = true;
    $('next').textContent = '正在生成结果…';
    try {
      const result = await request('/api/result', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({mode, attemptId, answers: answers.map((optionKey, index) => ({questionIndex: questions[index].index, optionKey}))})});
      if (Account.user?.id !== owner) throw new Error('登录状态已变化，请在原账号的个人中心查看结果');
      report = result;
      renderResult();
      storage.clear();
      location.hash = 'history/' + report.recordId;
      show('result');
    } catch (error) { notify('结果生成失败，答案已保留。点击按钮重试：' + error.message); }
    finally { busy = false; $('previous').disabled = current === 0; $('next').disabled = false; $('next').textContent = '查看我的结果 ↗'; }
  }
  function renderResult() {
    $('result-mode').textContent = `${labels[mode]} · ${mode === 'full' ? 60 : 20} 题已完成`;
    $('result-time').textContent = report.completedAt ? `完成于 ${Account.date(report.completedAt)} · 已保存到个人中心` : '';
    $('result-emoji').textContent = report.emoji;
    $('result-type').textContent = report.mbtiType;
    $('result-nickname').textContent = `${report.nickname} · ${report.animal}`;
    $('result-traits').textContent = report.traits;
    $('dimension-bars').replaceChildren();
    for (const [dim, names] of Object.entries(dimensions)) {
      const data = report.dimensions[dim];
      const bar = document.createElement('div'); bar.className = 'dim-bar';
      const row = document.createElement('div'); row.className = 'dim-bar-label';
      [data.left, data.right].forEach((side, index) => { const label = document.createElement('span'); label.textContent = `${names[index]} ${side.percent}%`; row.append(label); });
      const track = document.createElement('div'); track.className = 'dim-bar-track';
      const fill = document.createElement('div'); fill.className = 'dim-bar-fill'; fill.style.width = data.left.percent + '%';
      track.append(fill); bar.append(row, track); $('dimension-bars').append(bar);
    }
    for (const [id, field, tag] of [['result-strengths', 'strengths', 'li'], ['result-weaknesses', 'weaknesses', 'li'], ['result-careers', 'careers', 'span']]) {
      $(id).replaceChildren(...report[field].map(value => { const el = document.createElement(tag); el.textContent = value; return el; }));
    }
  }
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => start(button.dataset.mode)));
  $('resume').addEventListener('click', () => { const saved = readProgress(); if (saved) start(saved.mode, saved); });
  $('previous').addEventListener('click', () => { if (current > 0 && !busy) { current--; renderQuestion(); save(); } });
  $('next').addEventListener('click', () => {
    if (busy || !answers[current]) return;
    if (current < questions.length - 1) { current++; renderQuestion(); save(); }
    else submit();
  });
  function home() { if (busy) return; location.hash = 'home'; refreshResume(); show('home'); }
  document.querySelectorAll('.go-home').forEach(button => button.addEventListener('click', home));
  window.addEventListener('hashchange', () => {
    if (['#home', '#choose', '#dimensions', ''].includes(location.hash)) { show('home'); refreshResume(); if (location.hash === '#choose' || location.hash === '#dimensions') document.querySelector(location.hash).scrollIntoView(); }
    else if (location.hash === '#test' && questions.length) show('test');
    else if (location.hash === '#result' && report) show('result');
    else if (['#login','#register','#profile','#admin'].includes(location.hash) || /^#history\/\d+$/.test(location.hash)) return;
    else home();
  });
  $('download').addEventListener('click', () => {
    if (!report) return;
    const lines = ['本色 · 性格探索报告', `${labels[mode]} / ${mode === 'full' ? 60 : 20} 题 / ${report.completedAt ? Account.date(report.completedAt) : ''}`, `${report.mbtiType} · ${report.nickname} · ${report.animal}`, '', report.traits, '', '四个维度'];
    for (const [dim, names] of Object.entries(dimensions)) lines.push(`${names[0]} ${report.dimensions[dim].left.percent}% / ${names[1]} ${report.dimensions[dim].right.percent}%`);
    lines.push('', '可能的优势', ...report.strengths, '', '成长方向', ...report.weaknesses, '', '探索方向', ...report.careers, '', '本报告来自原创 MBTI 风格自我探索问卷，非官方量表，仅供参考。');
    const url = URL.createObjectURL(new Blob(['\ufeff' + lines.join('\n')], {type: 'text/plain;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = `本色-${report.mbtiType}-性格探索报告.txt`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  window.addEventListener('account-change', () => {
    if (identity !== Account.user?.id) {
      identity = Account.user?.id;
      questions = []; answers = []; current = 0; report = null; attemptId = null;
    }
    refreshResume();
  });
  window.addEventListener('open-history', event => {
    const record = event.detail;
    mode = record.mode; questions = []; answers = []; current = 0; attemptId = null;
    report = {...record.report, recordId:record.id, startedAt:record.startedAt, completedAt:record.completedAt};
    renderResult(); show('result');
  });
  Account.ready.then(refreshResume);
  if (location.hash === '#test' || location.hash === '#result') location.hash = 'home';
})();
