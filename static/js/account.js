/* 账号、历史记录与管理员界面；所有操作通过服务端鉴权。 */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let user = null, csrf = '', historyPage = 1, adminPage = 1, adminStatus = 'all';
  let routeVersion = 0;
  let adminAccountState = 'all', adminRows = [], adminLoading = false, resetTarget = null;
  const selectedUsers = new Set();
  let adminRequestVersion = 0;
  const modes = {simple: '简版测试', full: '完整版测试', pdp: 'PDP 动物人格', mental_age: '心理年龄测试', communication: '沟通风格测试', big_five: '大五人格测试'};
  const date = value => new Date(value).toLocaleString('zh-CN', {hour12:false});
  function element(tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  }
  function setUser(value) {
    const previous = user?.id;
    user = value;
    $('nav-account').textContent = user ? `${user.username} · 个人中心` : '登录 / 注册 ↗';
    $('nav-account').href = user ? '#profile' : '#login';
    $('nav-admin').hidden = !['admin','superadmin'].includes(user?.role);
    if (previous !== user?.id) {
      adminRequestVersion++; selectedUsers.clear(); adminRows=[];
      $('reset-password-dialog').close(); $('generated-passwords-dialog').close();
      $('admin-list').replaceChildren(); $('admin-notice').textContent='';
    }
    if (previous !== user?.id) window.dispatchEvent(new CustomEvent('account-change', {detail:user}));
  }
  async function api(url, options = {}) {
    const headers = {'Content-Type':'application/json', ...options.headers};
    if (options.method && options.method !== 'GET') headers['X-CSRF-Token'] = csrf;
    const response = await fetch(url, {...options, headers, credentials:'same-origin', signal:AbortSignal.timeout(25000)});
    let json;
    try { json = await response.json(); } catch { throw new Error('服务响应异常，请稍后重试'); }
    if (!response.ok || json.code !== 0) {
      if (response.status === 401 && !url.endsWith('/login')) { setUser(null); location.hash = 'login'; }
      const error = new Error(json.message || '请求失败'); error.status = response.status; throw error;
    }
    if (json.data?.csrfToken) csrf = json.data.csrfToken;
    return {data:json.data, message:json.message};
  }
  function requireLogin() {
    if (user) return true;
    location.hash = 'login';
    return false;
  }
  function show(name) {
    for (const screen of document.querySelectorAll('.screen')) screen.hidden = screen.id !== name + '-screen';
    window.scrollTo({top:0, behavior:'instant'});
    $(name + '-screen').querySelector('h1')?.focus({preventScroll:true});
  }
  function pageControls(prefix, data) {
    $(prefix + '-prev').disabled = data.page <= 1;
    $(prefix + '-next').disabled = data.page * data.pageSize >= data.total;
    $(prefix + '-page').textContent = `第 ${data.page} / ${Math.max(1, Math.ceil(data.total/data.pageSize))} 页`;
  }
  async function loadHistory() {
    const version = routeVersion;
    $('history-list').replaceChildren();
    $('history-state').textContent = '正在读取测试记录…';
    $('history-prev').disabled = $('history-next').disabled = true;
    try {
      const {data} = await api('/api/me/results?page=' + historyPage);
      if (version !== routeVersion) return;
      $('history-state').textContent = data.total ? `共 ${data.total} 次探索，按完成时间倒序排列` : '还没有测试记录。开始一次测试，结果就会出现在这里。';
      for (const item of data.items) {
        const card = element('article', undefined, 'history-card');
        const icon = element('span', item.emoji, 'history-emoji');
        const details = element('div');
        details.append(element('h3', `${item.mbtiType} · ${item.nickname}`), element('p', `${modes[item.mode]} · ${date(item.completedAt)}`, 'muted'));
        const link = element('a', '查看报告 ↗', 'text-button'); link.href = '#history/' + item.id;
        card.append(icon, details, link); $('history-list').append(card);
      }
      pageControls('history', data);
    } catch (error) { if (version === routeVersion) $('history-state').textContent = error.message + '；重新进入个人中心可重试。'; }
  }
  function notificationMessage(notice) {
    if (!notice) return '该账号没有注册邮件通知';
    if (notice.status === 'sent') return `审核邮件已发送 · ${date(notice.sentAt)}`;
    return `审核邮件未发送 · ${notice.lastError || '等待发送'}`;
  }
  function updateSelection() {
    const manageable = adminRows.filter(item => item.canManage);
    $('selection-count').textContent = `已选择 ${selectedUsers.size} 人`;
    $('select-all-users').disabled = adminLoading || !manageable.length;
    $('select-all-users').checked = manageable.length > 0 && selectedUsers.size === manageable.length;
    $('select-all-users').indeterminate = selectedUsers.size > 0 && selectedUsers.size < manageable.length;
    for (const id of ['bulk-activate','bulk-close','bulk-reset']) $(id).disabled = adminLoading || !selectedUsers.size;
    document.querySelectorAll('.user-management-actions button').forEach(button=>button.disabled=adminLoading);
    document.querySelectorAll('[data-user-select]').forEach(input => input.checked = selectedUsers.has(Number(input.dataset.userSelect)));
  }
  async function changeStates(ids, state) {
    adminLoading = true; updateSelection();
    $('admin-notice').textContent = '';
    try {
      const response = await api('/api/admin/users/state', {method:'POST',body:JSON.stringify({userIds:ids,accountState:state})});
      $('admin-notice').textContent = response.message;
      await loadAdmin();
    } catch (error) { $('admin-notice').textContent = error.message; }
    finally { adminLoading = false; updateSelection(); }
  }
  function openPasswordReset(item) {
    resetTarget = item.id;
    $('admin-reset-form').reset(); $('admin-reset-message').textContent = '';
    $('reset-target').textContent = `账号：${item.username}。重置后该用户需要使用新密码重新登录。`;
    $('reset-password-dialog').showModal();
  }
  async function loadAdmin() {
    const version = routeVersion;
    const requestVersion = ++adminRequestVersion;
    adminLoading = true; adminRows = []; selectedUsers.clear(); updateSelection();
    $('admin-list').replaceChildren();
    $('admin-state').textContent = '正在读取注册申请…';
    $('admin-prev').disabled = $('admin-next').disabled = true;
    try {
      const {data} = await api(`/api/admin/users?status=${adminStatus}&accountState=${adminAccountState}&page=${adminPage}`);
      if (version !== routeVersion || requestVersion !== adminRequestVersion) return;
      adminRows = data.items;
      $('admin-state').textContent = data.total ? `共 ${data.total} 个账号` : '当前分类暂无账号。';
      for (const item of data.items) {
        const card = element('article', undefined, 'review-card');
        const roleName = {admin:' · 管理员',superadmin:' · 超级管理员'}[item.role] || '';
        if (item.canManage) {
          const selection = element('label', undefined, 'user-selection');
          const checkbox = element('input'); checkbox.type = 'checkbox'; checkbox.dataset.userSelect = item.id;
          checkbox.addEventListener('change', () => { if (checkbox.checked) selectedUsers.add(item.id); else selectedUsers.delete(item.id); updateSelection(); });
          selection.append(checkbox, document.createTextNode(`选择 ${item.username}`)); card.append(selection);
        }
        card.append(element('h2', `${item.username}${roleName}`), element('p', `${item.email} · 注册于 ${date(item.createdAt)}`, 'muted'));
        const badges = element('div',undefined,'user-badges');
        badges.append(element('span',item.accountState === 'closed' ? '封闭' : '激活',item.accountState === 'closed' ? 'state-badge closed' : 'state-badge active'),
          element('span',{pending:'待审核',approved:'已通过审核',rejected:'审核未通过'}[item.status],'state-badge'));
        card.append(badges);
        if (item.canManage) {
          const actions = element('div',undefined,'user-management-actions');
          const reset = element('button','重置密码','text-button'); reset.addEventListener('click',() => openPasswordReset(item));
          const state = element('button',item.accountState === 'closed' ? '激活账号' : '封闭账号','text-button');
          state.addEventListener('click',async () => {state.disabled=true;try {await changeStates([item.id],item.accountState === 'closed' ? 'active' : 'closed');} finally {state.disabled=false;}});
          actions.append(reset,state); card.append(actions);
        }
        const mailRow = element('div', undefined, 'mail-row');
        mailRow.append(element('span', notificationMessage(item.notification), 'muted'));
        if (item.notification && item.notification.status !== 'sent') {
          const retry = element('button', '重试邮件 ↗', 'text-button');
          retry.addEventListener('click', async () => {
            retry.disabled = true;
            try { const response = await api(`/api/admin/notifications/${item.notification.id}/retry`, {method:'POST', body:'{}'}); $('admin-state').textContent = response.message; await loadAdmin(); }
            catch (error) { $('admin-state').textContent = error.message; retry.disabled = false; }
          });
          mailRow.append(retry);
        }
        card.append(mailRow);
        if (item.status === 'pending') {
          const label = element('label', '审核备注 / 拒绝原因', 'review-label');
          const input = element('textarea'); input.maxLength = 500; input.rows = 2; input.placeholder = '拒绝申请时请填写原因（最多 500 字）'; label.append(input);
          const buttons = element('div', undefined, 'review-actions');
          const message = element('p', '', 'form-message'); message.setAttribute('role','status');
          for (const [decision, name, cls] of [['approved','通过审核','primary-button'], ['rejected','拒绝申请','text-button']]) {
            const button = element('button', name, cls);
            button.addEventListener('click', async () => {
              if (decision === 'rejected' && !input.value.trim()) { message.textContent = '请填写拒绝原因'; input.focus(); return; }
              buttons.querySelectorAll('button').forEach(el => el.disabled = true);
              try { await api(`/api/admin/users/${item.id}/review`, {method:'POST', body:JSON.stringify({decision,note:input.value})}); await loadAdmin(); }
              catch (error) { message.textContent = error.message; buttons.querySelectorAll('button').forEach(el => el.disabled = false); }
            }); buttons.append(button);
          }
          card.append(label, buttons, message);
        } else if (item.reviewedAt) card.append(element('p', `审核于 ${date(item.reviewedAt)}${item.reviewNote ? ' · ' + item.reviewNote : ''}`, 'muted'));
        if (user.role === 'superadmin' && item.status === 'approved' && item.role !== 'superadmin') {
          const roleButton = element('button', item.role === 'admin' ? '取消管理员权限' : '设为管理员', 'text-button');
          roleButton.addEventListener('click', async () => {
            roleButton.disabled = true;
            try {
              await api(`/api/admin/users/${item.id}/role`, {method:'POST', body:JSON.stringify({role:item.role === 'admin' ? 'user' : 'admin'})});
              await loadAdmin();
            } catch (error) { $('admin-state').textContent = error.message; roleButton.disabled = false; }
          });
          card.append(roleButton);
        }
        $('admin-list').append(card);
      }
      pageControls('admin', data);
    } catch (error) { if (version === routeVersion && requestVersion === adminRequestVersion) $('admin-state').textContent = error.message; }
    finally { if (requestVersion === adminRequestVersion) {adminLoading = false; updateSelection();} }
  }
  async function route() {
    const hash = location.hash;
    const version = ++routeVersion;
    if (!['#login','#register','#profile','#admin'].includes(hash) && !/^#history\/\d+$/.test(hash)) return;
    if (hash === '#login' || hash === '#register') { show(hash.slice(1)); return; }
    if (!requireLogin(hash)) return;
    if (hash === '#profile') {
      show('profile'); $('profile-identity').textContent = `${user.username} · ${user.email} · 已通过审核`;
      await loadHistory();
    } else if (hash === '#admin') {
      show('admin');
      if (!['admin','superadmin'].includes(user.role)) { $('admin-list').replaceChildren(); $('admin-state').textContent = '该页面仅对管理员开放。'; return; }
      await loadAdmin();
    } else {
      show('profile'); $('history-state').textContent = '正在读取历史报告…';
      try {
        const {data} = await api('/api/me/results/' + hash.split('/')[1]);
        if (version === routeVersion) window.dispatchEvent(new CustomEvent('open-history', {detail:data}));
      } catch (error) { if (version === routeVersion) $('history-state').textContent = error.message; }
    }
  }
  function formHandler(id, handler) {
    $(id + '-form').addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.currentTarget, button = form.querySelector('button[type=submit]');
      button.disabled = true;
      const message = $(id + '-message'); message.textContent = ''; message.classList.remove('success');
      try { await ready; await handler(Object.fromEntries(new FormData(form)), message, form); }
      catch (error) { message.textContent = error.message; }
      finally { button.disabled = false; }
    });
  }
  formHandler('login', async (data, message, form) => {
    const response = await api('/api/auth/login', {method:'POST', body:JSON.stringify(data)});
    setUser(response.data.user); form.reset();
    location.hash = 'home';
  });
  formHandler('register', async (data, message, form) => {
    if (data.password !== data.confirmPassword) throw new Error('两次输入的密码不一致');
    const response = await api('/api/auth/register', {method:'POST', body:JSON.stringify(data)});
    form.reset(); message.textContent = response.message; message.classList.add('success');
  });
  formHandler('password', async (data, message, form) => {
    if (data.newPassword !== data.confirmPassword) throw new Error('两次输入的新密码不一致');
    const response = await api('/api/me/password', {method:'POST', body:JSON.stringify(data)});
    form.reset(); setUser(null); location.hash = 'login';
    $('login-message').textContent = response.message; $('login-message').classList.add('success');
  });
  $('logout').addEventListener('click', async () => {
    $('logout').disabled = true;
    try { await api('/api/auth/logout', {method:'POST', body:'{}'}); setUser(null); location.hash = 'login'; }
    catch (error) { $('history-state').textContent = error.message; }
    finally { $('logout').disabled = false; }
  });
  for (const prefix of ['history','admin']) {
    $(prefix + '-prev').addEventListener('click', () => { if (prefix === 'history') { historyPage--; loadHistory(); } else { adminPage--; loadAdmin(); } });
    $(prefix + '-next').addEventListener('click', () => { if (prefix === 'history') { historyPage++; loadHistory(); } else { adminPage++; loadAdmin(); } });
  }
  document.querySelectorAll('[data-status]').forEach(button => button.addEventListener('click', () => {
    adminStatus = button.dataset.status; adminPage = 1;
    document.querySelectorAll('[data-status]').forEach(el => el.setAttribute('aria-pressed',String(el === button)));
    loadAdmin();
  }));
  $('account-state-filter').addEventListener('change', event => {adminAccountState=event.target.value; adminPage=1; loadAdmin();});
  $('select-all-users').addEventListener('change',event => {
    selectedUsers.clear();
    if(event.target.checked) adminRows.filter(item=>item.canManage).forEach(item=>selectedUsers.add(item.id));
    updateSelection();
  });
  $('bulk-activate').addEventListener('click',()=>changeStates([...selectedUsers],'active'));
  $('bulk-close').addEventListener('click',()=>changeStates([...selectedUsers],'closed'));
  $('bulk-reset').addEventListener('click', async () => {
    const ids = [...selectedUsers]; if (!ids.length || adminLoading) return;
    adminLoading=true;updateSelection();$('admin-notice').textContent='';
    try {
      const response=await api('/api/admin/users/reset-password',{method:'POST',body:JSON.stringify({userIds:ids,generate:true})});
      $('generated-passwords').value=response.data.credentials.map(item=>`${item.username}\t${item.password}`).join('\n');
      $('generated-passwords-dialog').showModal();$('admin-notice').textContent=response.message;await loadAdmin();
    } catch(error){$('admin-notice').textContent=error.message;}
    finally {adminLoading=false;updateSelection();}
  });
  $('admin-reset-form').addEventListener('submit',async event=>{
    event.preventDefault(); const form=event.currentTarget; const values=Object.fromEntries(new FormData(form));
    if(values.newPassword!==values.confirmPassword){$('admin-reset-message').textContent='两次输入的新密码不一致';return;}
    const buttons=form.querySelectorAll('button');buttons.forEach(button=>button.disabled=true);
    try {
      const response=await api('/api/admin/users/reset-password',{method:'POST',body:JSON.stringify({userIds:[resetTarget],newPassword:values.newPassword})});
      $('reset-password-dialog').close();$('admin-notice').textContent=response.message;await loadAdmin();
    } catch(error){$('admin-reset-message').textContent=error.message;}
    finally {buttons.forEach(button=>button.disabled=false);}
  });
  document.querySelectorAll('[data-close-dialog]').forEach(button=>button.addEventListener('click',()=>$(button.dataset.closeDialog).close()));
  $('reset-password-dialog').addEventListener('close',()=>{$('admin-reset-form').reset();resetTarget=null;});
  $('generated-passwords-dialog').addEventListener('close',()=>{$('generated-passwords').value='';});
  $('download-generated-passwords').addEventListener('click',()=>{
    const url=URL.createObjectURL(new Blob(['\ufeff用户名\t新密码\n'+$('generated-passwords').value],{type:'text/plain;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download='本色-本次重置密码清单.txt';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  const ready = api('/api/auth/session').then(response => {setUser(response.data.user);}).catch(error => {
    $('login-message').textContent = '账号服务暂时不可用，请刷新后重试：' + error.message;
  });
  window.Account = {get user(){return user;}, ready, api, requireLogin, date};
  window.addEventListener('hashchange', () => { ready.then(route); });
  ready.then(route);
})();
