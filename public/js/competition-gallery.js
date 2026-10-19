(function(){
  const state = {
    list: [],
    filtered: [],
    seasons: [],
    currentSeason: 'all',
    currentType: 'all',
    searchText: ''
  };

  const els = {};

  function computeSeasonLabel(dateStr){
    // dateStr: YYYY-MM-DD
    try {
      const [yStr, mStr] = (dateStr||'').split('-');
      const y = parseInt(yStr,10);
      const m = parseInt(mStr,10);
      if(!y || !m) return '';
      if(m >= 9){
        return `${y}-${y+1}`;
      } else {
        return `${y-1}-${y}`;
      }
    } catch(e){
      return '';
    }
  }

  function buildSeasons(list){
    const set = new Set();
    list.forEach(item => {
      const s = computeSeasonLabel(item.date);
      if(s) set.add(s);
    });
    const arr = Array.from(set);
    // Sort ascending by first year
    arr.sort((a,b)=> parseInt(a.split('-')[0],10) - parseInt(b.split('-')[0],10));
    return arr;
  }

  function populateSeasonSelect(){
    if(!els.seasonSelect) return;
    els.seasonSelect.innerHTML = '';
    const optAll = document.createElement('option');
    optAll.value = 'all';
    optAll.textContent = 'All seasons';
    els.seasonSelect.appendChild(optAll);
    state.seasons.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      els.seasonSelect.appendChild(opt);
    });
    // Default to current season if present
    const today = new Date();
    const curSeason = computeSeasonLabel(`${today.getFullYear()}-${today.getMonth()+1}-01`);
    if(state.seasons.includes(curSeason)){
      els.seasonSelect.value = curSeason;
      state.currentSeason = curSeason;
    } else {
      els.seasonSelect.value = 'all';
      state.currentSeason = 'all';
    }
  }

  function competitionTypeLabel(item){
    return item.text.competition_type
   
  }

  function statusLabel(item){
    if(item && item.text && item.text.status) return item.text.status;
    // fallback mapping
    switch(Number(item.status)){
      case 2: return 'En cours';
      case 1: return 'Préparée';
      case 0: default: return 'Créée';
    }
  }

  function matchesFilters(item){
    // Type filter
    const typeLabel = String(item.competition_type);
    if(state.currentType !== 'all' && typeLabel !== state.currentType) return false;
    // Season filter
    const season = computeSeasonLabel(item.date);
    if(state.currentSeason !== 'all' && season !== state.currentSeason) return false;
    // Free text on title or gym
    const q = state.searchText.trim().toLowerCase();
    if(q){
      const title = (item.title||'').toLowerCase();
      const gym = (item.gym||'').toLowerCase();
      if(!title.includes(q) && !gym.includes(q)) return false;
    }
    return true;
  }

  function parseYYYYMMDD(dateStr){
    if(!dateStr) return null;
    const parts = String(dateStr).split('-');
    if(parts.length === 3){
      const y = parseInt(parts[0],10);
      const m = parseInt(parts[1],10) - 1;
      const d = parseInt(parts[2],10);
      if(!isNaN(y) && !isNaN(m) && !isNaN(d)) return new Date(y, m, d);
    }
    const d2 = new Date(dateStr);
    return isNaN(d2.getTime()) ? null : d2;
  }

  function renderGrid(){
    if(!els.grid) return;
    els.grid.innerHTML = '';
    const filtered = state.list
      .filter(matchesFilters)
      .slice()
      .sort((a,b)=>{
        const da = parseYYYYMMDD(a.date);
        const db = parseYYYYMMDD(b.date);
        if(da && db) return da - db; // earliest to latest
        if(da && !db) return -1;
        if(!da && db) return 1;
        return 0;
      });
    state.filtered = filtered;
    if(filtered.length === 0){
      const empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No competitions found.';
      els.grid.appendChild(empty);
      return;
    }
    const frag = document.createDocumentFragment();
    filtered.forEach(item => {
      const col = document.createElement('div');
      col.className = 'col-6 col-md-3';
      const card = document.createElement('div');
      card.className = 'fh5co-blog border-011 competition-card';

      const inner = document.createElement('div');
      inner.className = 'text-center';

      const link = document.createElement('a');
      link.href = item.url || (`/competitionDetails/${item.id}`);

      const blogText = document.createElement('div');
      blogText.className = 'blog-text';

      const contentWrap = document.createElement('div');

      const h3 = document.createElement('h3');
      h3.innerHTML = `${escapeHtml(item.title||'')}<br>${escapeHtml(item.date||'')}`;
      contentWrap.appendChild(h3);

      const typeSpan = document.createElement('span');
      typeSpan.className = 'posted_by';
      typeSpan.textContent = competitionTypeLabel(item);
      contentWrap.appendChild(typeSpan);
      contentWrap.appendChild(document.createElement('br'));

      const gymSpan = document.createElement('span');
      gymSpan.className = 'posted_by';
      gymSpan.innerHTML = `${escapeHtml(item.gym||'')}<br>`;
      contentWrap.appendChild(gymSpan);

      contentWrap.appendChild(document.createElement('br'));
      const img = document.createElement('img');
      img.src = `/image/${item.id}`;
      img.loading = 'lazy';
      img.className = 'competition-logo';
      blogText.appendChild(contentWrap);
      blogText.appendChild(img);
      blogText.appendChild(document.createElement('br'));
      blogText.appendChild(document.createElement('br'));

      const statusSpan = document.createElement('span');
      statusSpan.className = 'posted_by';
      statusSpan.textContent = statusLabel(item);
      blogText.appendChild(statusSpan);

      link.appendChild(blogText);
      inner.appendChild(link);
      card.appendChild(inner);
      col.appendChild(card);
      frag.appendChild(col);
    });
    els.grid.appendChild(frag);
  }

  function escapeHtml(str){
    return String(str).replace(/[&<>"']/g, s => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'
    })[s]);
  }

  function debounce(fn, delay){
    let t; return function(){
      clearTimeout(t);
      const args = arguments;
      t = setTimeout(()=> fn.apply(this,args), delay||200);
    };
  }

  function attachEvents(){
    if(els.search){
      els.search.addEventListener('input', debounce((e)=>{
        state.searchText = e.target.value || '';
        renderGrid();
      }, 200));
    }
    if(els.seasonSelect){
      els.seasonSelect.addEventListener('change', (e)=>{
        state.currentSeason = e.target.value || 'all';
        renderGrid();
      });
    }
    if(els.typeSelect){
      els.typeSelect.addEventListener('change', (e)=>{
        state.currentType = e.target.value || 'all';
        renderGrid();
      });
    }
  }

  async function load(){
    try {
      // Show a minimal loading indicator
      if(els.grid){
        els.grid.innerHTML = '<div class="loading">Loading competitions…</div>';
      }
      const data = await apiFetchJson('/api1/competition/list');
      if(!Array.isArray(data)) throw new Error('Unexpected competitions response');
      state.list = data;
      state.seasons = buildSeasons(state.list);
      populateSeasonSelect();
      renderGrid();
    } catch(err){
      console.error(err);
      if(els.grid){
        els.grid.innerHTML = '<div class="empty-state">Failed to load competitions.</div>';
      }
    }
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    els.search = document.getElementById('searchText');
    els.seasonSelect = document.getElementById('seasonSelect');
    els.typeSelect = document.getElementById('typeSelect');
    els.grid = document.getElementById('competitions-grid');
    attachEvents();
    load();
  });
})();
