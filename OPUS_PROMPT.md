# Prompt for Claude Opus: Build Patchy Frontend from Stitch Designs

---

## Context

You are building the frontend for **Patchy**, a multi-agent GitHub security bot. The UI designs have already been created in Google Stitch. Your job is to fetch those designs via Stitch MCP and transform them into a production-ready, backend-integration-ready web application.

---

## Project Information

**Stitch Project:**
- Title: Design System Implementation
- Project ID: `17255902636672467811`
- Screen: Scan History (ID: `7233a1fc06a245318d4a13b1fe8a2a61`)

**Technical Specifications:**
- Reference: `TECHNICAL_SPEC.md` in the project directory
- Backend: Flask (Python)
- Frontend: HTML + TailwindCSS + Vanilla JavaScript
- Authentication: GitHub OAuth
- APIs: GitHub API, Cerebras LLM API

---

## Your Task

### Step 1: Fetch Stitch Designs
Use the Stitch MCP to:
1. List all screens in project `17255902636672467811`
2. Download the HTML, CSS, and image assets for each screen
3. Download any screenshots for reference

### Step 2: Build Production-Ready Frontend
Transform the Stitch designs into a complete frontend with these requirements:

#### File Structure
```
patchy/
├── app.py                          # Flask backend (you'll create structure only)
├── static/
│   ├── css/
│   │   ├── main.css               # Compiled from Stitch + custom styles
│   │   └── tailwind.css           # TailwindCSS
│   ├── js/
│   │   ├── main.js                # Global JavaScript
│   │   ├── dashboard.js           # Dashboard-specific logic
│   │   ├── scan.js                # Scan functionality
│   │   └── api.js                 # API client (IMPORTANT: Backend integration layer)
│   └── images/
│       └── [Stitch exported images]
├── templates/
│   ├── base.html                  # Base template with nav/footer
│   ├── index.html                 # Landing page
│   ├── dashboard.html             # Repository dashboard
│   ├── scan_results.html          # Scan history
│   ├── scan_detail.html           # Individual scan details
│   └── components/
│       ├── navbar.html            # Reusable navbar
│       ├── repo_card.html         # Repository card component
│       ├── finding_card.html      # Security finding card
│       └── loading.html           # Loading states
└── requirements.txt
```

#### Critical Requirements

**1. Backend Integration Points**
Add clear comments at every point where backend data will be injected:

```html
<!-- BACKEND: Inject user data here -->
<!-- Expected data structure:
{
  "username": "string",
  "avatar_url": "string",
  "repos_count": number
}
-->
<div class="user-info">
  <img src="{{ user.avatar_url }}" alt="{{ user.username }}">
  <span>{{ user.username }}</span>
</div>
```

**2. API Integration Layer**
Create `static/js/api.js` with placeholder functions for all backend calls:

```javascript
// API Client for Patchy Backend
// TODO: Update BASE_URL when backend is deployed

const API = {
  BASE_URL: '/api',  // BACKEND: Update this in production
  
  // Authentication
  async login() {
    // BACKEND: Redirects to /login endpoint
    window.location.href = '/login';
  },
  
  async logout() {
    // BACKEND: POST to /logout
    // TODO: Implement when backend ready
  },
  
  // Repositories
  async fetchRepos() {
    // BACKEND: GET /api/repos
    // Returns: Array of { id, name, language, last_scan, ... }
    // TODO: Replace with actual fetch when backend ready
    return MOCK_DATA.repos;
  },
  
  async scanRepo(repoId) {
    // BACKEND: POST /api/scan
    // Body: { repo_id: repoId }
    // Returns: { scan_id, status, ... }
    // TODO: Implement when backend ready
    return { scan_id: '123', status: 'scanning' };
  },
  
  // Scans
  async fetchScanHistory() {
    // BACKEND: GET /api/scans
    // Returns: Array of scan results
    // TODO: Replace with actual fetch when backend ready
    return MOCK_DATA.scans;
  },
  
  async fetchScanDetails(scanId) {
    // BACKEND: GET /api/scans/:id
    // Returns: Detailed scan with findings
    // TODO: Implement when backend ready
    return MOCK_DATA.scanDetails;
  }
};

// MOCK DATA for frontend development
// BACKEND: Remove this when API is ready
const MOCK_DATA = {
  repos: [
    { id: 1, name: 'user/repo-1', language: 'Python', last_scan: '2 days ago' },
    { id: 2, name: 'user/repo-2', language: 'JavaScript', last_scan: 'Never' }
  ],
  scans: [
    { 
      id: 1, 
      repo: 'user/repo-1', 
      timestamp: '2 mins ago',
      findings: { critical: 3, medium: 5, low: 2 },
      pr_url: 'https://github.com/user/repo-1/pull/42'
    }
  ],
  scanDetails: {
    findings: [
      {
        severity: 'critical',
        type: 'SQL Injection',
        file: 'app.py',
        line: 42,
        description: 'User input directly in query',
        fix: '// Fixed code here'
      }
    ]
  }
};
```

**3. Flask Template Structure**
Use Jinja2 templating with clear placeholders:

```html
<!-- base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{% block title %}Patchy{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
  <!-- BACKEND: Add any dynamic meta tags here -->
</head>
<body>
  {% include 'components/navbar.html' %}
  
  <main>
    {% block content %}{% endblock %}
  </main>
  
  <script src="{{ url_for('static', filename='js/api.js') }}"></script>
  <script src="{{ url_for('static', filename='js/main.js') }}"></script>
  {% block scripts %}{% endblock %}
</body>
</html>
```

**4. Component-Based Architecture**
Break down Stitch designs into reusable components:

```html
<!-- components/repo_card.html -->
<!-- BACKEND: Pass repo object to this component -->
<!-- Expected props: { id, name, language, last_scan, is_scanning } -->

<div class="repo-card" data-repo-id="{{ repo.id }}">
  <div class="repo-header">
    <h3>{{ repo.name }}</h3>
    <span class="badge badge-{{ repo.language|lower }}">{{ repo.language }}</span>
  </div>
  
  <div class="repo-meta">
    <span>Last scan: {{ repo.last_scan or 'Never' }}</span>
  </div>
  
  <div class="repo-actions">
    <!-- BACKEND: Disable button if is_scanning is true -->
    <button 
      class="btn-primary scan-btn" 
      data-repo-id="{{ repo.id }}"
      {% if repo.is_scanning %}disabled{% endif %}
    >
      {% if repo.is_scanning %}
        Scanning...
      {% else %}
        Scan Now
      {% endif %}
    </button>
  </div>
</div>
```

**5. State Management**
Add clear state management for dynamic UI:

```javascript
// static/js/dashboard.js

// STATE: Track scanning repos
const scanningRepos = new Set();

// BACKEND: This will be called when scan button is clicked
async function handleScanClick(repoId) {
  // Update UI to show loading
  scanningRepos.add(repoId);
  updateRepoCard(repoId, { is_scanning: true });
  
  try {
    // BACKEND: Call scan API
    const result = await API.scanRepo(repoId);
    
    // BACKEND: Poll for scan status or use WebSocket
    // TODO: Implement polling/WebSocket when backend ready
    pollScanStatus(result.scan_id);
    
  } catch (error) {
    console.error('Scan failed:', error);
    // Show error message
    showError('Scan failed. Please try again.');
  }
}

// BACKEND: Poll scan status until complete
async function pollScanStatus(scanId) {
  // TODO: Implement when backend provides status endpoint
  // Expected endpoint: GET /api/scans/:id/status
  // Returns: { status: 'scanning' | 'complete' | 'failed' }
}
```

**6. Loading & Error States**
Include all UI states from Stitch designs:

```html
<!-- Loading State -->
<div class="loading-state" id="loading-scan">
  <div class="spinner"></div>
  <h2>Scanning...</h2>
  <ul class="progress-steps">
    <li class="complete">✓ Cloning repository</li>
    <li class="active">⏳ Running security scan</li>
    <li class="pending">⏳ Generating fixes</li>
    <li class="pending">⏳ Creating pull request</li>
  </ul>
  <p>This may take 1-2 minutes</p>
</div>

<!-- Error State -->
<div class="error-state" id="error-scan" style="display: none;">
  <div class="error-icon">⚠️</div>
  <h2>Scan Failed</h2>
  <p id="error-message"><!-- BACKEND: Inject error message --></p>
  <button class="btn-primary" onclick="retryLastScan()">Try Again</button>
</div>
```

**7. Responsive Design**
Ensure all Stitch designs work on mobile:
- Use TailwindCSS responsive classes
- Test on mobile viewport
- Add mobile navigation if needed

**8. Accessibility**
- Add ARIA labels to all interactive elements
- Ensure keyboard navigation works
- Add focus states
- Use semantic HTML

**9. Dark/Light Mode**
Implement theme toggle if Stitch provided both modes:

```javascript
// Theme management
const theme = {
  current: localStorage.getItem('theme') || 'dark',
  
  toggle() {
    this.current = this.current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', this.current);
    localStorage.setItem('theme', this.current);
  },
  
  init() {
    document.documentElement.setAttribute('data-theme', this.current);
  }
};

theme.init();
```

---

## Code Quality Standards

### Comments
Add comments at these levels:

1. **File-level**: Purpose of the file
2. **Section-level**: What each major section does
3. **Backend integration**: Where backend data is needed
4. **TODO markers**: What needs to be implemented when backend is ready

Example:
```javascript
/**
 * Dashboard Controller
 * Manages repository list, scan triggers, and real-time updates
 * 
 * BACKEND DEPENDENCIES:
 * - GET /api/repos - Fetch user repositories
 * - POST /api/scan - Trigger repository scan
 * - WebSocket /ws/scan-updates - Real-time scan progress (optional)
 */

// TODO: Replace mock data with actual API calls when backend is ready
// TODO: Implement WebSocket for real-time updates
// TODO: Add error handling for API failures
```

### Naming Conventions
- CSS classes: kebab-case (e.g., `repo-card`, `scan-btn`)
- JavaScript: camelCase (e.g., `fetchRepos`, `handleScanClick`)
- Files: lowercase with underscores (e.g., `scan_results.html`)
- Constants: UPPER_SNAKE_CASE (e.g., `API_BASE_URL`)

### Code Organization
- Keep HTML templates clean and readable
- Extract complex logic to JavaScript modules
- Use CSS custom properties for theming
- Group related functions together

---

## Deliverables

1. **Complete file structure** as specified above
2. **All HTML templates** converted from Stitch designs
3. **CSS files** with Stitch styles + custom additions
4. **JavaScript files** with API client and mock data
5. **README.md** with:
   - Setup instructions
   - How to run locally
   - Backend integration guide
   - Mock data structure documentation
6. **INTEGRATION_GUIDE.md** explaining:
   - All API endpoints needed
   - Expected request/response formats
   - WebSocket events (if applicable)
   - Authentication flow

---

## Testing Checklist

Before considering the frontend complete, verify:

- [ ] All Stitch screens are implemented
- [ ] Navigation works between all pages
- [ ] Mock data displays correctly in all components
- [ ] Loading states show during async operations
- [ ] Error states display when simulated
- [ ] Responsive design works on mobile (375px) and desktop (1920px)
- [ ] Dark mode toggle works (if applicable)
- [ ] All buttons and links have hover states
- [ ] Console has no errors
- [ ] Code is well-commented with backend integration points
- [ ] All TODO markers are clear and actionable

---

## Example Output Structure

When you're done, the project should look like this:

```
patchy/
├── README.md                       ✓ Setup instructions
├── INTEGRATION_GUIDE.md            ✓ Backend integration docs
├── requirements.txt                ✓ Python dependencies (Flask, etc.)
├── app.py                          ✓ Flask app skeleton
├── static/
│   ├── css/
│   │   ├── main.css               ✓ All styles from Stitch + custom
│   │   └── components.css         ✓ Component-specific styles
│   ├── js/
│   │   ├── api.js                 ✓ API client with mock data
│   │   ├── main.js                ✓ Global functionality
│   │   ├── dashboard.js           ✓ Dashboard logic
│   │   └── scan.js                ✓ Scan functionality
│   └── images/                     ✓ All Stitch images
└── templates/
    ├── base.html                   ✓ Base template
    ├── index.html                  ✓ Landing page
    ├── dashboard.html              ✓ Dashboard
    ├── scan_results.html           ✓ Scan history
    ├── scan_detail.html            ✓ Scan details
    └── components/                 ✓ Reusable components
```

---

## Important Notes

1. **Don't implement the backend** - just create the structure and integration points
2. **Use mock data** - make it realistic so the UI looks good
3. **Comment heavily** - the next developer needs to understand where to plug in the backend
4. **Make it production-ready** - clean code, no hacks, proper error handling
5. **Follow the technical spec** - reference `TECHNICAL_SPEC.md` for architecture decisions
6. **Keep it simple** - don't over-engineer, but make it extensible

---

## Success Criteria

The frontend is complete when:
1. ✅ A developer can open `index.html` and see a beautiful, functional UI
2. ✅ All interactions work with mock data
3. ✅ A backend developer can read `INTEGRATION_GUIDE.md` and know exactly what APIs to build
4. ✅ The code is clean, commented, and ready for production
5. ✅ The design matches the Stitch mockups pixel-perfect

---

**Start by fetching the Stitch designs, then build the frontend following these guidelines. Good luck!**
