# Binary Grid Animation - Design Specification

## Visual Description

Create an interactive background animation with binary digits (0 and 1) arranged in a grid pattern.

---

## Layout

**Grid Structure:**
- Binary digits (0 and 1) arranged in a uniform grid across the entire page
- Spacing: 30-40px between each digit
- Font: Monospace (JetBrains Mono or Fira Code)
- Font size: 12-14px

---

## Default State (No Mouse Interaction)

**Appearance:**
- All digits are **dull/dim** - low brightness
- Color: Light gray with low opacity
  - `rgba(139, 144, 160, 0.15)` - very subtle, barely visible
- Random mix of 0s and 1s across the grid
- Static - no movement or animation

**Visual Example:**
```
0 1 0 1 0 1 0 1 0 1
1 0 1 0 1 0 1 0 1 0
0 1 0 1 0 1 0 1 0 1
1 0 1 0 1 0 1 0 1 0
```
All very dim, barely noticeable

---

## Mouse Interaction (When Mouse Moves Near)

**Behavior:**

1. **Brightness Increase:**
   - Digits within 150-200px radius of mouse cursor become **brighter**
   - Smooth transition from dim to bright
   - Closer to mouse = brighter
   - No glow, no blur - just increased opacity/brightness

2. **Digit Flipping:**
   - When mouse moves near, digits **flip** between 0 and 1
   - 0 becomes 1
   - 1 becomes 0
   - Smooth transition (not instant)
   - Creates a "wave" effect as mouse moves

3. **Color Scheme:**
   - Bright digits use two alternating colors:
     - **Primary Blue**: `#adc6ff` (rgb(173, 198, 255))
     - **Secondary Green**: `#4edea3` (rgb(78, 222, 163))
   - Alternate colors in a checkerboard pattern OR randomly
   - When dim: all same gray color
   - When bright: reveal blue/green colors

---

## Animation Details

**Transition Speed:**
- Brightness change: 200-300ms smooth transition
- Digit flip: 150ms
- Mouse influence fades smoothly with distance

**Distance-Based Intensity:**
```
Distance from mouse:
- 0-50px:   100% brightness (fully visible)
- 50-100px: 70% brightness
- 100-150px: 40% brightness
- 150-200px: 20% brightness
- 200px+:   15% brightness (default dim state)
```

**No Effects to Avoid:**
- ❌ No glowing halos
- ❌ No blur effects
- ❌ No shadows
- ❌ No particle trails
- ❌ No falling/raining animation

**Keep It:**
- ✅ Clean and minimal
- ✅ Subtle when not interacting
- ✅ Responsive to mouse movement
- ✅ Smooth transitions
- ✅ Modern and professional

---

## Technical Implementation Notes

**Canvas or CSS:**
- Use HTML5 Canvas for performance
- Or CSS Grid with JavaScript for simpler approach

**Performance:**
- Should run at 60fps
- Optimize for large grids (100+ digits)
- Use requestAnimationFrame

**Responsive:**
- Grid adjusts to screen size
- Works on desktop (mouse) and mobile (touch - optional)

---

## Reference Aesthetic

**Similar to:**
- Vercel's homepage background
- Linear's landing page
- Stripe's interactive backgrounds
- Modern SaaS landing pages

**Mood:**
- Subtle and elegant
- Not distracting
- Adds depth without overwhelming content
- Professional and modern
- Tech-focused aesthetic

---

## Color Palette Reference

```css
/* Default (Dim) */
--digit-dim: rgba(139, 144, 160, 0.15);

/* Bright (Near Mouse) */
--digit-blue: #adc6ff;      /* Primary */
--digit-green: #4edea3;     /* Secondary */

/* Background */
--bg-color: #10131b;        /* Dark navy */
```

---

## Example Behavior Flow

1. **Page loads** → Grid of dim 0s and 1s appears
2. **User moves mouse** → Digits near cursor brighten and flip
3. **Mouse moves away** → Digits fade back to dim and may flip back
4. **Continuous movement** → Creates a "revealing" wave effect
5. **Mouse leaves page** → All digits return to dim state

---

## Final Result

A subtle, interactive binary grid that:
- Adds visual interest without distraction
- Reinforces the "tech/security" theme
- Feels modern and polished
- Responds elegantly to user interaction
- Maintains readability of foreground content

---

**Priority:** High visual polish, smooth performance, subtle elegance
**Avoid:** Flashy effects, distracting animations, performance issues
