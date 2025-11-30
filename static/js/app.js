// Wait for DOM to be ready
(function() {
  'use strict';
  
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));
  
  // Initialize all components when DOM is ready
  function initAll() {
    initMenuToggle();
    initThemeToggle();
  }
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
  
  // Performance helpers
  function throttle(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
  
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
  
  // Initialize menu toggle when DOM is ready
  function initMenuToggle() {
    const menuToggle = document.getElementById('menuToggle');
    const dropdownMenu = document.getElementById('dropdownMenu');
    
    if (!menuToggle || !dropdownMenu) {
      console.warn('Menu toggle elements not found', { menuToggle, dropdownMenu });
      return;
    }
    
    console.log('Menu toggle initialized', { menuToggle, dropdownMenu });
    
    const toggleMenu = (e) => {
      console.log('Toggle menu called', e);
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      
      const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true';
      const newState = !isExpanded;
      
      console.log('Menu state:', { isExpanded, newState });
      
      menuToggle.setAttribute('aria-expanded', newState.toString());
      
      if (newState) {
        dropdownMenu.classList.add('show');
        console.log('Menu opened, classes:', dropdownMenu.className);
      } else {
        dropdownMenu.classList.remove('show');
        console.log('Menu closed, classes:', dropdownMenu.className);
      }
      
      // Add visual feedback
      menuToggle.style.transform = 'scale(0.95)';
      setTimeout(() => {
        menuToggle.style.transform = '';
      }, 150);
    };

    // Click event
    menuToggle.addEventListener('click', (e) => {
      console.log('Menu toggle clicked');
      toggleMenu(e);
    });
    
    // Touch events for mobile
    menuToggle.addEventListener('touchend', (e) => {
      console.log('Menu toggle touched');
      e.preventDefault();
      toggleMenu(e);
    }, { passive: false });
    
    // Visual feedback on touch
    menuToggle.addEventListener('touchstart', () => {
      menuToggle.style.opacity = '0.7';
    }, { passive: true });
    
    menuToggle.addEventListener('touchend', () => {
      setTimeout(() => {
        menuToggle.style.opacity = '';
      }, 150);
    }, { passive: true });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (menuToggle && dropdownMenu) {
        const target = e.target;
        if (!menuToggle.contains(target) && !dropdownMenu.contains(target)) {
          menuToggle.setAttribute('aria-expanded', 'false');
          dropdownMenu.classList.remove('show');
        }
      }
    });

    // Close menu when clicking menu items (but let them execute first)
    const menuItems = dropdownMenu.querySelectorAll('a, button');
    menuItems.forEach(el => {
      el.addEventListener('click', (e) => {
        // Don't prevent default - let the link/button work
        setTimeout(() => {
          if (menuToggle && dropdownMenu) {
            menuToggle.setAttribute('aria-expanded', 'false');
            dropdownMenu.classList.remove('show');
          }
        }, 100);
      });
    });
    
    // Close menu on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && menuToggle && dropdownMenu) {
        const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true';
        if (isExpanded) {
          menuToggle.setAttribute('aria-expanded', 'false');
          dropdownMenu.classList.remove('show');
        }
      }
    });
    
    // Ensure button is clickable
    menuToggle.style.pointerEvents = 'auto';
    menuToggle.style.cursor = 'pointer';
    menuToggle.setAttribute('tabindex', '0');
    
    // Ensure dropdown is properly positioned
    dropdownMenu.style.zIndex = '1004';
    dropdownMenu.style.pointerEvents = 'auto';
  }
  
  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMenuToggle);
  } else {
    // DOM is already ready
    initMenuToggle();
  }

  // Theme toggle
  function initThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
      const saved = localStorage.getItem('theme') || 'light';
      document.documentElement.dataset.theme = saved;
      themeToggle.addEventListener('click', () => {
        const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.dataset.theme = next;
        localStorage.setItem('theme', next);
      });
    }
  }

  // Back to top - throttled scroll
  const backToTop = $("#backToTop");
  if (backToTop) {
    window.addEventListener('scroll', throttle(() => {
      backToTop.classList.toggle('show', window.scrollY > 600);
    }, 100), { passive: true });
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
  const searchContainer = $("#searchContainer");
  const searchBox = $("#postSearchInput");
  
  if (postList && searchContainer) {
    // Show search container if there are posts
    const existingPosts = postList.querySelectorAll('.post-card, .post-card-modern').length;
    if (existingPosts > 0 || postTemplate) {
      searchContainer.style.display = 'block';
    }
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
      postList.innerHTML = `
        <div class="empty-posts" style="grid-column: 1 / -1;">
          <div class="empty-posts-icon">🌱</div>
          <h3>Zatiaľ žiadne príspevky</h3>
          <p class="muted">Buď prvý, kto zdieľa svoju skúsenosť s rastlinami!</p>
        </div>
      `;
      return;
    }
    list.forEach(async (post) => {
      const tmpl = postTemplate.content.cloneNode(true);
      const li = tmpl.querySelector("li");
      li.dataset.id = post.id;
      li.classList.add('post-card-modern');
      
      // Set up author link
      const authorLink = tmpl.querySelector(".author-link-template");
      if (authorLink) {
        authorLink.href = `/user/${post.author || 'unknown'}`;
        authorLink.classList.remove('author-link-template');
      }
      
      // Set up author name and time
      const authorName = tmpl.querySelector(".post-author-name");
      if (authorName) authorName.textContent = post.author || "Anonym";
      
      const timeEl = tmpl.querySelector(".post-time");
      if (timeEl) timeEl.textContent = formatDate(post.created_at);
      
      // Set up avatar placeholder
      const avatarPlaceholder = tmpl.querySelector(".avatar-placeholder-small");
      if (avatarPlaceholder && post.author) {
        avatarPlaceholder.textContent = post.author[0].toUpperCase();
      }
      
      // Set up content
      const contentEl = tmpl.querySelector(".post-content-text");
      if (contentEl) {
        contentEl.innerHTML = escapeHTML(post.content || '');
      }
      
      // Set up like button
      const likeBtn = tmpl.querySelector(".like-btn-modern");
      const likeCount = tmpl.querySelector(".like-count");
      if (likeBtn && likeCount) {
        likeBtn.setAttribute('data-post-id', post.id);
        likeCount.setAttribute('data-post-id', post.id);
        likeCount.textContent = post.like_count || 0;
        const emoji = likeBtn.querySelector('.action-icon');
        if (post.liked) {
          likeBtn.classList.add('liked');
          if (emoji) emoji.textContent = '❤️';
        } else {
          likeBtn.classList.remove('liked');
          if (emoji) emoji.textContent = '🤍';
        }
      }
      
      // Set up comment button
      const commentBtn = tmpl.querySelector(".comment-link-template");
      const commentCount = tmpl.querySelector(".comment-count");
      if (commentBtn && commentCount) {
        commentBtn.href = `/posts/${post.id}`;
        commentBtn.classList.remove('comment-link-template');
        commentCount.setAttribute('data-post-id', post.id);
        commentCount.textContent = post.comment_count || 0;
      }
      
      // Set up image with lazy loading
      if (post.image_path) {
        const imgContainer = tmpl.querySelector(".post-image-container");
        const contentLink = tmpl.querySelector(".post-content-link");
        if (imgContainer || contentLink) {
          const imageWrapper = document.createElement('div');
          imageWrapper.className = 'post-image-wrapper';
          const img = document.createElement('img');
          img.src = `/static/${post.image_path}`;
          img.alt = 'Obrázok príspevku';
          img.className = 'post-image';
          img.loading = 'lazy';
          imageWrapper.appendChild(img);
          
          // Insert image inside the content link if it exists
          if (contentLink) {
            contentLink.appendChild(imageWrapper);
          } else if (imgContainer) {
            // Fallback: use old structure
            imgContainer.appendChild(imageWrapper);
          }
        }
      }

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
    const query = (searchBox && searchBox.value ? searchBox.value : '').toLowerCase();
    const filtered = !query ? data : data.filter(p => (p.content||'').toLowerCase().includes(query) || (p.author||'').toLowerCase().includes(query));
    renderPosts(filtered);
  }

  // Filter server-rendered posts client-side if no dynamic rendering
  // Cache card selectors for better performance
  let cachedCards = null;
  function filterServerRenderedPosts() {
    if (!postList || !searchBox) return;
    const query = searchBox.value.toLowerCase();
    if (!cachedCards) {
      cachedCards = Array.from(postList.querySelectorAll('.post-card, .post-card-modern')).map(card => ({
        element: card,
        content: (card.querySelector('.post-content, .post-content-text')?.textContent || '').toLowerCase(),
        author: (card.querySelector('.author, .post-author-name')?.textContent || '').toLowerCase()
      }));
    }
    cachedCards.forEach(({element, content, author}) => {
      const matches = !query || content.includes(query) || author.includes(query);
      element.style.display = matches ? '' : 'none';
    });
  }

  if (searchBox) {
    // Cache server-rendered posts selector
    const hasServerRenderedPosts = postList && postList.querySelectorAll('.post-card, .post-card-modern').length > 0;
    
    // Debounce search input
    searchBox.addEventListener('input', debounce(() => {
      // If using dynamic rendering (template exists), use loadPosts
      // Otherwise filter server-rendered posts client-side
      if (postTemplate && postList.querySelectorAll('.post-card, .post-card-modern').length === 0) {
        loadPosts();
      } else {
        filterServerRenderedPosts();
      }
    }, 300));
  }

  const postForm = $("#postForm");
  const postInput = $("#postInput");
  const fileInput = $("#fileInput");
  if (postForm) {
    postForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const content = (postInput?.value || '').trim();
      if (!content) return;
      const formData = new FormData();
      formData.append('content', content);
      if (fileInput && fileInput.files && fileInput.files[0]) {
        formData.append('file', fileInput.files[0]);
      }
      const res = await fetch('/api/posts', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        if (postInput) postInput.value = '';
        if (fileInput) fileInput.value = '';
        const preview = document.getElementById('imagePreview');
        if (preview) preview.style.display = 'none';
        // Reload page to show new post with server-rendered template
        window.location.reload();
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

  // Only load posts if using dynamic rendering (not if posts are already rendered server-side)
  if (postList && postTemplate && postList.querySelectorAll('.post-card, .post-card-modern').length === 0) {
    loadPosts();
  }
  
  // Like buttons (delegated)
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.like-btn') || e.target.closest('.like-btn-modern');
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const postId = btn.getAttribute('data-post-id');
    if (!postId) return;
    
    try {
      const res = await fetch(`/like/${postId}`, { method: 'POST' });
      if (!res.ok) {
        console.error('Like failed:', res.status);
        return;
      }
      const data = await res.json();
      const countEls = document.querySelectorAll(`.like-count[data-post-id='${postId}'], #likeCount`);
      countEls.forEach(el => { el.textContent = data.count || 0; });
      
      // Update button state with animation
      const emoji = btn.querySelector('.action-icon') || btn.querySelector('.like-emoji') || btn;
      if (data.liked) {
        btn.classList.add('liked');
        if (emoji && emoji.tagName === 'SPAN') {
          emoji.textContent = '❤️';
        } else if (emoji) {
          emoji.textContent = '❤️';
        }
      } else {
        btn.classList.remove('liked');
        if (emoji && emoji.tagName === 'SPAN') {
          emoji.textContent = '🤍';
        } else if (emoji) {
          emoji.textContent = '🤍';
        }
      }
    } catch (err) {
      console.error('Like error:', err);
    }
  });

  // Follow form
  const followForm = document.getElementById('followForm');
  if (followForm) {
    followForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = followForm.getAttribute('data-username');
      const btn = document.getElementById('followBtn');
      const isUnfollow = (btn && btn.textContent.trim().toLowerCase() === 'unfollow');
      const url = isUnfollow ? `/unfollow/${username}` : `/follow/${username}`;
      const res = await fetch(url, { method: 'POST' });
      if (!res.ok) return;
      const data = await res.json();
      if (btn) btn.textContent = data.following ? 'Unfollow' : 'Follow';
      const f1 = document.getElementById('followersCount');
      const f2 = document.getElementById('followingCount');
      if (f1 && typeof data.followers === 'number') f1.textContent = `Sledujúci: ${data.followers}`;
      if (f2 && typeof data.following_count === 'number') f2.textContent = `Sleduje: ${data.following_count}`;
    });
  }
})();

// ============================================
// Mobile-Specific Enhancements
// ============================================

(() => {
  // Prevent double-tap zoom on buttons and links
  let lastTouchEnd = 0;
  document.addEventListener('touchend', (e) => {
    const now = Date.now();
    if (now - lastTouchEnd <= 300) {
      e.preventDefault();
    }
    lastTouchEnd = now;
  }, false);

  // Smooth scroll for mobile
  if ('scrollBehavior' in document.documentElement.style) {
    // Native smooth scroll supported
  } else {
    // Fallback for older browsers
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#' && href.length > 1) {
          e.preventDefault();
          const target = document.querySelector(href);
          if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }
      });
    });
  }

  // Bottom navigation active state management
  const bottomNavItems = document.querySelectorAll('.bottom-nav-item');
  const currentPath = window.location.pathname;
  
  bottomNavItems.forEach(item => {
    const href = item.getAttribute('href');
    if (href && currentPath.includes(href.split('/').pop())) {
      item.classList.add('active');
    }
    
    // Add touch feedback
    item.addEventListener('touchstart', function() {
      this.style.opacity = '0.7';
    });
    
    item.addEventListener('touchend', function() {
      setTimeout(() => {
        this.style.opacity = '';
      }, 150);
    });
  });

  // Optimize images for mobile (lazy loading already handled)
  if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
            observer.unobserve(img);
          }
        }
      });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
      imageObserver.observe(img);
    });
  }

  // Prevent pull-to-refresh on mobile (optional - can be removed if you want native behavior)
  let touchStartY = 0;
  document.addEventListener('touchstart', (e) => {
    touchStartY = e.touches[0].clientY;
  }, { passive: true });

  document.addEventListener('touchmove', (e) => {
    const touchY = e.touches[0].clientY;
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    
    // Prevent pull-to-refresh when at top and scrolling down
    if (scrollTop === 0 && touchY > touchStartY) {
      // Allow small movement for better UX
      if (touchY - touchStartY > 50) {
        e.preventDefault();
      }
    }
  }, { passive: false });

  // Add haptic feedback for actions (if supported)
  const hapticFeedback = (type = 'light') => {
    if ('vibrate' in navigator) {
      const patterns = {
        light: 10,
        medium: 20,
        heavy: 30
      };
      navigator.vibrate(patterns[type] || 10);
    }
  };

  // Add haptic feedback to important actions
  document.addEventListener('click', (e) => {
    const target = e.target.closest('.like-btn-modern, .action-btn, .btn-primary, .publish-btn');
    if (target) {
      hapticFeedback('light');
    }
  });

  // Optimize scroll performance on mobile
  let ticking = false;
  const handleScroll = () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        // Update back to top button visibility
        const backToTop = document.getElementById('backToTop');
        if (backToTop) {
          if (window.scrollY > 600) {
            backToTop.classList.add('show');
          } else {
            backToTop.classList.remove('show');
          }
        }
        ticking = false;
      });
      ticking = true;
    }
  };

  window.addEventListener('scroll', handleScroll, { passive: true });

  // Improve form input experience on mobile
  const inputs = document.querySelectorAll('input, textarea');
  inputs.forEach(input => {
    // Prevent zoom on focus (iOS)
    if (input.type !== 'date' && input.type !== 'time') {
      const fontSize = window.getComputedStyle(input).fontSize;
      if (parseFloat(fontSize) < 16) {
        input.style.fontSize = '16px';
      }
    }

    // Add better focus handling
    input.addEventListener('focus', function() {
      // Scroll input into view with some offset
      setTimeout(() => {
        this.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 300);
    });
  });

  // Handle orientation change
  let resizeTimer;
  window.addEventListener('orientationchange', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      // Recalculate layouts after orientation change
      window.dispatchEvent(new Event('resize'));
    }, 100);
  });

  // Add swipe gestures for cards (optional enhancement)
  let touchStartX = 0;
  let touchStartY = 0;
  
  document.addEventListener('touchstart', (e) => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }, { passive: true });

  document.addEventListener('touchend', (e) => {
    if (!touchStartX || !touchStartY) return;
    
    const touchEndX = e.changedTouches[0].clientX;
    const touchEndY = e.changedTouches[0].clientY;
    
    const diffX = touchStartX - touchEndX;
    const diffY = touchStartY - touchEndY;
    
    // Reset
    touchStartX = 0;
    touchStartY = 0;
    
    // Detect swipe (only if significant and mostly horizontal)
    if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
      // Swipe detected - could be used for navigation or actions
      // This is a placeholder for future swipe functionality
    }
  }, { passive: true });
})();


