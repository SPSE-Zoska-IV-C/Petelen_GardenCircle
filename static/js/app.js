(() => {
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));
  // Theme toggle
  const themeToggle = $("#themeToggle");
  if (themeToggle) {
    const saved = localStorage.getItem('theme') || 'light';
    document.documentElement.dataset.theme = saved;
    themeToggle.addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      localStorage.setItem('theme', next);
    });
  }

  // Back to top
  const backToTop = $("#backToTop");
  if (backToTop) {
    window.addEventListener('scroll', () => {
      backToTop.classList.toggle('show', window.scrollY > 600);
    });
    backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  // Active nav link highlight
  const links = $$(".main-nav a");
  const path = window.location.pathname + window.location.hash;
  links.forEach(a => {
    if (path.includes(a.getAttribute('href'))) a.classList.add('active');
  });

  // Post search/filter
  const postList = $("#postList");
  const postTemplate = document.getElementById("post-template");
  const searchBox = document.createElement('input');
  if (postList) {
    searchBox.type = 'search';
    searchBox.placeholder = 'Hľadať v príspevkoch…';
    searchBox.className = 'search-input';
    postList.parentElement.insertBefore(searchBox, postList);
  }

  function escapeHTML(str = "") {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatDate(ts) {
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  }

  async function fetchPosts() {
    const res = await fetch('/api/posts');
    if (!res.ok) return [];
    return res.json();
  }

  function renderPosts(list) {
    if (!postList) return;
    postList.innerHTML = "";
    if (!list || !list.length) {
      postList.innerHTML = "<li class='muted'>Zatiaľ žiadne príspevky — buď prvý!</li>";
      return;
    }
    list.forEach(async (post) => {
      const tmpl = postTemplate.content.cloneNode(true);
      const li = tmpl.querySelector("li");
      li.dataset.id = post.id;
      tmpl.querySelector(".author").textContent = post.author || "Anonym";
      const timeEl = tmpl.querySelector(".time");
      timeEl.textContent = formatDate(post.created_at);
      tmpl.querySelector(".post-content").innerHTML = escapeHTML(post.content);

      const commentForm = tmpl.querySelector(".comment-form");
      commentForm.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const input = commentForm.querySelector(".comment-input");
        const text = input.value.trim();
        if (!text) return;
        const res = await fetch(`/api/posts/${post.id}/comments`, {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({ author: "Navštevník", text })
        });
        if (res.ok) {
          // Append the new comment without full reload
          const c = await res.json();
          const commentList = commentForm.parentElement.querySelector('.comment-list');
          const li = document.createElement('li');
          li.innerHTML = `<strong>${escapeHTML(c.author)}</strong> • <small class="muted">${formatDate(Date.now())}</small><div>${escapeHTML(c.text)}</div>`;
          commentList.appendChild(li);
          input.value = "";
        }
      });

      // Load existing comments for this post
      try {
        const cres = await fetch(`/api/posts/${post.id}/comments`);
        if (cres.ok) {
          const comments = await cres.json();
          const commentList = tmpl.querySelector('.comment-list');
          comments.forEach(c => {
            const cli = document.createElement('li');
            cli.innerHTML = `<strong>${escapeHTML(c.author || 'Anonym')}</strong> • <small class="muted">${formatDate(c.created_at)}</small><div>${escapeHTML(c.text)}</div>`;
            commentList.appendChild(cli);
          });
        }
      } catch {}

      const deleteBtn = tmpl.querySelector(".delete-post");
      deleteBtn.addEventListener("click", async () => {
        if (!confirm("Naozaj chcete vymazať tento príspevok?")) return;
        await fetch(`/api/posts/${post.id}`, { method: "DELETE" });
        await loadPosts();
      });

      postList.appendChild(tmpl);
    });
  }

  async function loadPosts() {
    if (!postList) return;
    const data = await fetchPosts();
    const query = (searchBox.value || '').toLowerCase();
    const filtered = !query ? data : data.filter(p => (p.content||'').toLowerCase().includes(query) || (p.author||'').toLowerCase().includes(query));
    renderPosts(filtered);
  }

  if (searchBox) searchBox.addEventListener('input', loadPosts);

  const postForm = $("#postForm");
  const postInput = $("#postInput");
  const authorInput = $("#authorInput");
  if (postForm) {
    postForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const content = postInput.value.trim();
      const author = authorInput.value.trim() || "Anonym";
      if (!content) return;
      const res = await fetch('/api/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ author, content })
      });
      if (res.ok) {
        postInput.value = '';
        authorInput.value = '';
        await loadPosts();
      }
    });
  }

  // Articles on home page (optional)
  const articlesContainer = $("#articlesContainer");
  if (articlesContainer) {
    fetch('/static/articles.json')
      .then(r => r.json())
      .then(data => {
        articlesContainer.innerHTML = '';
        data.forEach(a => {
          const d = document.createElement('article');
          d.className = 'article-card';
          d.innerHTML = `<h3>${escapeHTML(a.title)}</h3><p>${escapeHTML(a.content)}</p>`;
          articlesContainer.appendChild(d);
        })
      })
      .catch(() => {
        articlesContainer.innerHTML = "<p class='muted'>Nepodarilo sa načítať články.</p>";
      });
  }

  loadPosts();
})();


