// GardenCircle — app.js (vanilla JS, modular, localStorage)
// Minimal dependencies: none. Designed for clarity and safety.
// IMPORTANT: update BACKEND_URL if your backend runs elsewhere.
(() => {
    const BACKEND_URL = "http://127.0.0.1:8000";
    const STORAGE_KEY = "gardencircle_posts_v1";
  
    // Helpers
    const $ = (s, root=document) => root.querySelector(s);
    const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));
  
    function uid(prefix = "") {
      return prefix + Math.random().toString(36).slice(2, 9);
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
      const d = new Date(ts);
      return d.toLocaleString(); // uses user locale
    }
  
    // Data
    let posts = [];
  
    function loadPosts() {
      try {
        posts = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
      } catch (e) {
        posts = [];
      }
    }
  
    function savePosts() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(posts));
    }
  
    // Rendering
    const postList = $("#postList");
    const postTemplate = document.getElementById("post-template");
  
    function renderPosts() {
      postList.innerHTML = "";
      if (!posts.length) {
        postList.innerHTML = "<li class='muted'>Zatiaľ žiadne príspevky — buď prvý!</li>";
        return;
      }
  
      posts.slice().reverse().forEach(post => {
        const tmpl = postTemplate.content.cloneNode(true);
        const li = tmpl.querySelector("li");
        li.dataset.id = post.id;
        tmpl.querySelector(".author").textContent = post.author || "Anonym";
        const timeEl = tmpl.querySelector(".time");
        timeEl.textContent = formatDate(post.createdAt);
        timeEl.setAttribute("datetime", new Date(post.createdAt).toISOString());
        tmpl.querySelector(".post-content").innerHTML = escapeHTML(post.content);
  
        // Comments
        const commentList = tmpl.querySelector(".comment-list");
        if (post.comments && post.comments.length) {
          post.comments.forEach(c => {
            const cli = document.createElement("li");
            cli.dataset.cid = c.id;
            cli.innerHTML = `<strong>${escapeHTML(c.author||"Anonym")}</strong> • <small class="muted">${formatDate(c.createdAt)}</small><div>${escapeHTML(c.text)}</div>`;
            commentList.appendChild(cli);
          });
        }
  
        // attach actions
        const commentForm = tmpl.querySelector(".comment-form");
        commentForm.addEventListener("submit", (ev) => {
          ev.preventDefault();
          const input = commentForm.querySelector(".comment-input");
          const text = input.value.trim();
          if (!text) return;
          addComment(post.id, { id: uid("c_"), text, author: "Navštevník", createdAt: Date.now() });
          input.value = "";
        });
  
        const deleteBtn = tmpl.querySelector(".delete-post");
        deleteBtn.addEventListener("click", () => {
          if (!confirm("Naozaj chcete vymazať tento príspevok?")) return;
          deletePost(post.id);
        });
  
        postList.appendChild(tmpl);
      });
    }
  
    // CRUD
    function addPost(author, content) {
      const p = {
        id: uid("p_"),
        author: author || "Anonym",
        content: content,
        createdAt: Date.now(),
        comments: []
      };
      posts.push(p);
      savePosts();
      renderPosts();
    }
  
    function deletePost(id) {
      posts = posts.filter(p => p.id !== id);
      savePosts();
      renderPosts();
    }
  
    function addComment(postId, comment) {
      const idx = posts.findIndex(p => p.id === postId);
      if (idx === -1) return;
      posts[idx].comments = posts[idx].comments || [];
      posts[idx].comments.push(comment);
      savePosts();
      renderPosts();
    }
  
    // Init posts form
    const postForm = $("#postForm");
    const postInput = $("#postInput");
    const authorInput = $("#authorInput");
  
    postForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const content = postInput.value.trim();
      const author = authorInput.value.trim();
      if (!content) return;
      addPost(author || "Anonym", content);
      postInput.value = "";
      authorInput.value = "";
      window.location.hash = "#feed"; // keep focus area
    });
  
    // Load articles (fallback to static file)
    async function loadArticles() {
      try {
        const res = await fetch("articles.json");
        if (!res.ok) throw new Error("articles.json not found");
        const data = await res.json();
        const container = $("#articlesContainer");
        container.innerHTML = "";
        data.forEach(a => {
          const d = document.createElement("article");
          d.className = "article-card";
          d.innerHTML = `<h3>${escapeHTML(a.title)}</h3><p>${escapeHTML(a.content)}</p>`;
          container.appendChild(d);
        });
      } catch (err) {
        console.warn("Chyba načítania článkov:", err);
        $("#articlesContainer").innerHTML = "<p class='muted'>Nepodarilo sa načítať články.</p>";
      }
    }
  
    // Chatbot UI + network
    const chatWindow = $("#chatWindow");
    const chatForm = $("#chatForm");
    const chatInput = $("#chatInput");
  
    function appendChat(role, text, ts = Date.now()) {
      const row = document.createElement("div");
      row.className = "chat-row";
      const bubble = document.createElement("div");
      bubble.className = "chat-bubble " + (role === "user" ? "chat-user" : "chat-bot");
      bubble.innerHTML = `<strong class="muted">${role === "user" ? "Ty" : "Bot"}</strong><div>${escapeHTML(text)}</div><small class="muted">${formatDate(ts)}</small>`;
      row.appendChild(bubble);
      chatWindow.appendChild(row);
      chatWindow.scrollTop = chatWindow.scrollHeight;
    }
  
    async function sendToBot(message) {
      const url = `${BACKEND_URL}/chatbot`;
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({message})
        });
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(`Server error: ${res.status} ${txt}`);
        }
        const data = await res.json();
        return data.reply || "Bot neodpovedal.";
      } catch (err) {
        console.error("chat error", err);
        return `Chyba pri komunikácii s botom: ${err.message}`;
      }
    }
  
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = chatInput.value.trim();
      if (!text) return;
      appendChat("user", text);
      chatInput.value = "";
      // show loading
      const loadingId = uid("l_");
      appendChat("bot", "…", Date.now());
      const reply = await sendToBot(text);
      // remove last bot placeholder (simpler: re-render last)
      // For simplicity, append actual reply:
      appendChat("bot", reply);
    });
  
    // Startup
    loadPosts();
    renderPosts();
    loadArticles();
  
    // Expose for debugging (optional)
    window.GardenCircle = {
      loadPosts, savePosts, posts, addPost, deletePost, addComment
    };
  })();
  