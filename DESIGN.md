# Patchy - Design Specification

> UI/UX Design for Multi-Agent GitHub Security Bot

## Design Tool
**Using**: Stitch by Google (https://stitch.google.com)
- Generate initial designs
- Export code as base
- Iterate and improve

---

## 1. Design Principles

### Minimalist
- Clean, simple interface
- Focus on core actions
- No clutter

### Developer-Friendly
- Dark mode by default
- Code-focused aesthetics
- GitHub-like feel

### Fast
- Instant feedback
- Loading states
- Real-time updates

---

## 2. Color Palette

```css
/* Dark Theme (Primary) */
--bg-primary: #0d1117        /* Main background */
--bg-secondary: #161b22      /* Cards, panels */
--bg-tertiary: #21262d       /* Hover states */

--text-primary: #c9d1d9      /* Main text */
--text-secondary: #8b949e    /* Secondary text */
--text-muted: #6e7681        /* Muted text */

--accent-primary: #58a6ff    /* Links, buttons */
--accent-success: #3fb950    /* Success states */
--accent-warning: #d29922    /* Warning states */
--accent-danger: #f85149     /* Error states */

--border: #30363d            /* Borders */
```

---

## 3. Typography

```css
/* Fonts */
--font-primary: 'Inter', -apple-system, sans-serif
--font-mono: 'JetBrains Mono', 'Fira Code', monospace

/* Sizes */
--text-xs: 0.75rem    /* 12px */
--text-sm: 0.875rem   /* 14px */
--text-base: 1rem     /* 16px */
--text-lg: 1.125rem   /* 18px */
--text-xl: 1.25rem    /* 20px */
--text-2xl: 1.5rem    /* 24px */
--text-3xl: 2rem      /* 32px */
```

---

## 4. Page Designs

### 4.1 Landing Page (`/`)

**Layout**:
```
┌─────────────────────────────────────────┐
│  [Logo] Patchy        [Login with GitHub]│
├─────────────────────────────────────────┤
│                                         │
│         🛡️ Patchy                       │
│    AI Security Teammate                 │
│    for Your GitHub Repos                │
│                                         │
│    [Get Started with GitHub]            │
│                                         │
│  ✓ Auto-scan vulnerabilities            │
│  ✓ Generate fixes automatically         │
│  ✓ Respond to issues intelligently      │
│                                         │
└─────────────────────────────────────────┘
```

**Components**:
- Hero section with gradient background
- Large CTA button (GitHub login)
- 3 feature highlights
- Simple footer

---

### 4.2 Dashboard (`/dashboard`)

**Layout**:
```
┌─────────────────────────────────────────┐
│ [Logo] Patchy    [@username] [Logout]   │
├─────────────────────────────────────────┤
│                                         │
│  Your Repositories                      │
│  ┌─────────────────────────────────┐   │
│  │ 🔍 Search repos...              │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 📦 username/repo-name           │   │
│  │ Python • Last scan: 2 days ago  │   │
│  │                    [Scan Now]   │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 📦 username/another-repo        │   │
│  │ JavaScript • Never scanned      │   │
│  │                    [Scan Now]   │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

**Components**:
- Top navigation bar
- Search/filter for repos
- Repo cards with:
  - Repo name + icon
  - Language badge
  - Last scan timestamp
  - "Scan Now" button
- Empty state if no repos

---

### 4.3 Scan Results (`/scans`)

**Layout**:
```
┌─────────────────────────────────────────┐
│ [Logo] Patchy    [@username] [Logout]   │
├─────────────────────────────────────────┤
│                                         │
│  Scan History                           │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ username/repo-name              │   │
│  │ Scanned: 2 mins ago             │   │
│  │                                 │   │
│  │ 🔴 3 Critical  🟡 5 Medium      │   │
│  │                                 │   │
│  │ PR Created: #42                 │   │
│  │ [View PR] [View Details]        │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ username/another-repo           │   │
│  │ Scanned: 1 day ago              │   │
│  │                                 │   │
│  │ ✅ No issues found              │   │
│  │                                 │   │
│  │ [View Details]                  │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

**Components**:
- Scan history cards
- Severity badges (Critical, High, Medium, Low)
- PR links
- Expandable details

---

### 4.4 Scan Detail View (Modal/Page)

**Layout**:
```
┌─────────────────────────────────────────┐
│  Scan Results: username/repo-name       │
│  Commit: abc123 • 2 mins ago            │
├─────────────────────────────────────────┤
│                                         │
│  Findings (8)                           │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 🔴 SQL Injection                │   │
│  │ app.py:42                       │   │
│  │                                 │   │
│  │ User input directly in query    │   │
│  │ Severity: Critical              │   │
│  │                                 │   │
│  │ [View Fix]                      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 🟡 Hardcoded Secret             │   │
│  │ config.py:15                    │   │
│  │                                 │   │
│  │ API key found in source code    │   │
│  │ Severity: Medium                │   │
│  │                                 │   │
│  │ [View Fix]                      │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

**Components**:
- Finding cards with:
  - Severity icon + color
  - Vulnerability type
  - File + line number
  - Description
  - "View Fix" button (shows diff)

---

### 4.5 Loading States

**Scanning in Progress**:
```
┌─────────────────────────────────────────┐
│                                         │
│         🔄 Scanning...                  │
│                                         │
│    ✓ Cloning repository                │
│    ⏳ Running security scan             │
│    ⏳ Generating fixes                  │
│    ⏳ Creating pull request             │
│                                         │
│    This may take 1-2 minutes            │
│                                         │
└─────────────────────────────────────────┘
```

---

## 5. Components Library

### 5.1 Buttons

```html
<!-- Primary Button -->
<button class="btn-primary">
  Scan Now
</button>

<!-- Secondary Button -->
<button class="btn-secondary">
  View Details
</button>

<!-- GitHub Button -->
<button class="btn-github">
  <svg><!-- GitHub icon --></svg>
  Login with GitHub
</button>
```

**Styles**:
```css
.btn-primary {
  background: var(--accent-primary);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-weight: 500;
}

.btn-primary:hover {
  background: #1f6feb;
}
```

---

### 5.2 Cards

```html
<div class="card">
  <div class="card-header">
    <h3>username/repo-name</h3>
    <span class="badge">Python</span>
  </div>
  <div class="card-body">
    <p>Last scan: 2 days ago</p>
  </div>
  <div class="card-footer">
    <button class="btn-primary">Scan Now</button>
  </div>
</div>
```

**Styles**:
```css
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
}
```

---

### 5.3 Badges

```html
<!-- Severity Badges -->
<span class="badge-critical">Critical</span>
<span class="badge-high">High</span>
<span class="badge-medium">Medium</span>
<span class="badge-low">Low</span>

<!-- Language Badge -->
<span class="badge-lang">Python</span>
```

---

### 5.4 Navigation

```html
<nav class="navbar">
  <div class="nav-left">
    <img src="logo.svg" alt="Patchy" />
    <span>Patchy</span>
  </div>
  <div class="nav-right">
    <span>@username</span>
    <button class="btn-secondary">Logout</button>
  </div>
</nav>
```

---

## 6. Responsive Design

### Breakpoints
```css
/* Mobile */
@media (max-width: 640px) {
  /* Stack cards vertically */
  /* Hide secondary info */
}

/* Tablet */
@media (min-width: 641px) and (max-width: 1024px) {
  /* 2-column grid */
}

/* Desktop */
@media (min-width: 1025px) {
  /* 3-column grid */
  /* Show all info */
}
```

---

## 7. Animations

### Scan Progress
```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.scanning-icon {
  animation: spin 2s linear infinite;
}
```

### Card Hover
```css
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transition: all 0.2s ease;
}
```

---

## 8. Icons

**Using**: Heroicons or Lucide Icons
- 🔍 Search
- 📦 Repository
- 🔴 Critical
- 🟡 Warning
- ✅ Success
- 🔄 Loading
- 🛡️ Security

---

## 9. Stitch Export Workflow

1. Go to https://stitch.google.com
2. Create new project: "Patchy Dashboard"
3. Design each page:
   - Landing page
   - Dashboard
   - Scan results
4. Export HTML/CSS code
5. Copy to `/templates` and `/static`
6. Integrate with Flask routes
7. Add dynamic data with Jinja2

---

## 10. Implementation Checklist

- [ ] Export landing page from Stitch
- [ ] Export dashboard from Stitch
- [ ] Export scan results from Stitch
- [ ] Create component library
- [ ] Add TailwindCSS for utilities
- [ ] Implement dark mode
- [ ] Add loading states
- [ ] Add error states
- [ ] Test responsive design
- [ ] Add animations

---

**Document Version**: 1.0  
**Last Updated**: 2026-04-23  
**Design Tool**: Stitch by Google
