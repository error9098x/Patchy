# Stitch Prompts for Patchy

> Copy these prompts into Stitch by Google to generate page designs

---

## 1. Landing Page

### Prompt for Stitch:

```
Create a modern landing page for a GitHub security bot called "Patchy".

Visual style:
- Dark mode with deep navy/black background (#0d1117)
- Clean, minimal, developer-focused aesthetic
- Similar to GitHub's design language
- Subtle gradients and glass morphism effects

Layout:
- Top navigation bar with logo on left, "Login with GitHub" button on right
- Hero section in center with large heading "Patchy" and tagline "AI Security Teammate for Your GitHub Repos"
- Large prominent button "Get Started with GitHub" with GitHub icon
- Three feature cards below in a row showing: "Auto-scan vulnerabilities", "Generate fixes automatically", "Respond to issues intelligently"
- Each feature has an icon (shield, code, chat bubble)
- Minimal footer at bottom

Colors:
- Background: Very dark blue-black
- Text: Light gray/white
- Primary button: Bright blue (#58a6ff)
- Accent: Green for success elements
- Cards: Slightly lighter than background with subtle border

Typography:
- Modern sans-serif font (Inter or similar)
- Large bold heading for hero
- Medium weight for body text
- Monospace font for any code snippets

Include:
- Subtle animations on hover
- Smooth transitions
- Professional spacing and padding
- Responsive design that works on mobile

Also create a light mode version with:
- White/light gray background
- Dark text
- Same blue accent color
- Softer shadows instead of glows
```

---

## 2. Dashboard Page

### Prompt for Stitch:

```
Create a dashboard page for a GitHub security scanning tool.

Visual style:
- Dark mode interface matching GitHub's design
- Clean, organized, data-focused layout
- Professional developer tool aesthetic

Layout:
- Top navigation bar with logo, username display, and logout button
- Page heading "Your Repositories"
- Search bar below heading with magnifying glass icon
- Grid of repository cards (3 columns on desktop, 1 on mobile)
- Each card shows:
  - Repository icon and name (e.g., "username/repo-name")
  - Language badge (Python, JavaScript, etc.)
  - Last scan timestamp or "Never scanned"
  - "Scan Now" button at bottom right
- Empty state message if no repositories: "No repositories found. Connect your GitHub account."

Card design:
- Slightly elevated from background
- Rounded corners
- Subtle border
- Hover effect: slight lift and glow
- Language badge: small colored pill (Python=blue, JavaScript=yellow, etc.)

Colors:
- Background: Dark navy (#0d1117)
- Cards: Slightly lighter (#161b22)
- Text: Light gray
- Scan button: Bright blue
- Language badges: Color-coded by language

Include:
- Loading skeleton for cards while fetching
- Hover states for interactive elements
- Smooth transitions
- Responsive grid layout

Also create light mode version with white background and subtle shadows.
```

---

## 3. Scan Results Page

### Prompt for Stitch:

```
Create a scan results history page showing security scan outcomes.

Visual style:
- Dark mode, developer-focused interface
- Data visualization aesthetic
- Clear hierarchy of information

Layout:
- Top navigation bar (same as dashboard)
- Page heading "Scan History"
- List of scan result cards (stacked vertically)
- Each card shows:
  - Repository name at top
  - Timestamp "Scanned: X mins/hours/days ago"
  - Severity badges in a row: "3 Critical", "5 Medium", "2 Low" with colored dots
  - If PR was created: "PR Created: #42" with link
  - Two buttons at bottom: "View PR" and "View Details"
  - If no issues: Large green checkmark with "No issues found"

Card design:
- Larger than dashboard cards
- Expandable/collapsible for details
- Severity indicators: Red dot for critical, yellow for medium, gray for low
- PR link styled as GitHub link (blue, underlined on hover)

Colors:
- Critical: Red (#f85149)
- High: Orange (#d29922)
- Medium: Yellow (#e3b341)
- Low: Gray (#8b949e)
- Success: Green (#3fb950)
- Background: Dark navy
- Cards: Slightly lighter with border

Include:
- Empty state: "No scans yet. Go to Dashboard to scan a repository."
- Loading state while fetching results
- Smooth expand/collapse animations
- Hover effects on cards

Also create light mode version.
```

---

## 4. Scan Detail Modal/Page

### Prompt for Stitch:

```
Create a detailed view showing individual security findings from a scan.

Visual style:
- Dark mode, technical/code-focused design
- Similar to code review interfaces
- Clear visual hierarchy for severity

Layout:
- Header showing: Repository name, commit hash, timestamp
- "Findings (8)" heading
- List of finding cards (stacked vertically)
- Each finding card shows:
  - Severity icon and color (red circle for critical, yellow for medium)
  - Vulnerability type as heading (e.g., "SQL Injection")
  - File path and line number (e.g., "app.py:42")
  - Brief description of the issue
  - Severity badge
  - "View Fix" button that expands to show code diff
- Code diff section (when expanded):
  - Side-by-side or unified diff view
  - Red background for removed lines
  - Green background for added lines
  - Line numbers on left
  - Syntax highlighting

Card design:
- Border color matches severity (red border for critical, yellow for medium)
- Slightly elevated
- Expandable for code diff
- Monospace font for file paths and code

Colors:
- Critical findings: Red accent (#f85149)
- Medium findings: Yellow accent (#d29922)
- Low findings: Gray accent
- Code diff removed: Dark red background
- Code diff added: Dark green background
- Background: Dark navy
- Cards: Slightly lighter

Include:
- Smooth expand/collapse for code diffs
- Syntax highlighting in code blocks
- Copy button for code snippets
- Filter/sort options at top (by severity, file, type)

Also create light mode version.
```

---

## 5. Loading State

### Prompt for Stitch:

```
Create a loading/scanning progress screen.

Visual style:
- Dark mode, centered layout
- Animated, engaging but professional
- Clear progress indication

Layout:
- Centered vertically and horizontally
- Large spinning icon or animation at top (security shield or scanning radar)
- "Scanning..." heading below icon
- Progress checklist showing steps:
  - ✓ Cloning repository (completed - green checkmark)
  - ⏳ Running security scan (in progress - spinning icon)
  - ⏳ Generating fixes (pending - gray)
  - ⏳ Creating pull request (pending - gray)
- Estimated time text: "This may take 1-2 minutes"
- Optional: Progress bar at bottom

Animation:
- Smooth spinning/pulsing animation for main icon
- Checkmarks animate in when step completes
- Subtle fade-in for each step

Colors:
- Background: Dark navy
- Icon: Bright blue with glow effect
- Completed steps: Green
- In-progress: Blue with animation
- Pending: Gray
- Text: Light gray

Include:
- Smooth animations
- Professional loading indicators
- Clear visual feedback

Also create light mode version.
```

---

## 6. Error State

### Prompt for Stitch:

```
Create an error message component for when scans fail.

Visual style:
- Dark mode, clear but not alarming
- Friendly error messaging
- Actionable next steps

Layout:
- Centered card or banner
- Error icon (red X or alert triangle)
- Error heading: "Scan Failed"
- Error message: Brief explanation of what went wrong
- Suggested actions in bullet points
- "Try Again" button
- "Contact Support" link

Colors:
- Background: Dark navy
- Card: Slightly lighter with red accent border
- Icon: Red (#f85149)
- Text: Light gray
- Button: Blue (not red - we want to encourage action)

Include:
- Not too aggressive/scary
- Helpful and actionable
- Professional tone

Also create light mode version.
```

---

## Usage Instructions

1. Go to https://stitch.google.com
2. Create new project: "Patchy"
3. Copy each prompt above into Stitch
4. Generate the design
5. Adjust colors/spacing if needed
6. Export HTML/CSS code
7. Save to `/templates` and `/static` folders

---

## Color Reference for Stitch

**Dark Mode:**
- Background: #0d1117
- Cards: #161b22
- Text: #c9d1d9
- Accent Blue: #58a6ff
- Success Green: #3fb950
- Warning Yellow: #d29922
- Error Red: #f85149

**Light Mode:**
- Background: #ffffff
- Cards: #f6f8fa
- Text: #24292f
- Accent Blue: #0969da
- Success Green: #1a7f37
- Warning Yellow: #9a6700
- Error Red: #cf222e

---

**Last Updated**: 2026-04-23
