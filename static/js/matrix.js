/**
 * Interactive Binary Grid
 * Dim 0s and 1s across page. Mouse proximity brightens and flips bits.
 * Spec: BINARY_ANIMATION_PROMPT.md
 */

(() => {
    const canvas = document.getElementById('binary-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const SPACING = 34;
    const FONT_SIZE = 13;
    const MAX_DIST = 190;
    const FLIP_MS = 150;
    const FADE_MS = 260;

    let width = 0, height = 0;
    let cells = [];
    let mouse = { x: -9999, y: -9999, active: false };

    function resize() {
        width = window.innerWidth;
        
        // Calculate height up to footer (not beyond)
        const footer = document.querySelector('footer');
        if (footer) {
            const footerTop = footer.offsetTop;
            height = footerTop;
        } else {
            // Fallback to full document height
            height = Math.max(
                document.body.scrollHeight,
                document.documentElement.scrollHeight,
                window.innerHeight
            );
        }
        
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.font = `600 ${FONT_SIZE}px "JetBrains Mono", "Fira Code", ui-monospace, monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        buildGrid();
    }

    function buildGrid() {
        cells = [];
        const cols = Math.ceil(width / SPACING) + 1;
        const rows = Math.ceil(height / SPACING) + 1;
        const offsetX = (width - (cols - 1) * SPACING) / 2;
        const offsetY = (height - (rows - 1) * SPACING) / 2;
        for (let c = 0; c < cols; c++) {
            for (let r = 0; r < rows; r++) {
                const bit = Math.random() < 0.5 ? 0 : 1;
                cells.push({
                    x: offsetX + c * SPACING,
                    y: offsetY + r * SPACING,
                    bit,
                    displayBit: bit,
                    flipStart: 0,
                    flipProgress: 1,
                    brightness: 0,
                    targetBrightness: 0,
                    // checkerboard color choice
                    green: ((c + r) % 2) === 1,
                    lastFlip: 0,
                });
            }
        }
    }

    function draw(t) {
        ctx.clearRect(0, 0, width, height);
        const dt = 16;

        for (let i = 0; i < cells.length; i++) {
            const cell = cells[i];
            const dx = mouse.x - cell.x;
            const dy = mouse.y - cell.y;
            const dist = Math.hypot(dx, dy);

            let target = 0;
            if (mouse.active && dist < MAX_DIST) {
                target = 1 - (dist / MAX_DIST);
                target = Math.pow(target, 1.4);
            }
            cell.targetBrightness = target;

            // smooth fade
            const fadeStep = dt / FADE_MS;
            if (cell.brightness < cell.targetBrightness) {
                cell.brightness = Math.min(cell.targetBrightness, cell.brightness + fadeStep);
            } else if (cell.brightness > cell.targetBrightness) {
                cell.brightness = Math.max(cell.targetBrightness, cell.brightness - fadeStep);
            }

            // flip trigger: cells near mouse periodically flip
            if (target > 0.35 && t - cell.lastFlip > 800 + Math.random() * 1200) {
                cell.bit = 1 - cell.bit;
                cell.flipStart = t;
                cell.flipProgress = 0;
                cell.lastFlip = t;
            }
            
            // Random background twinkling - like stars
            // Probability: 10/25 = 0.4 per second
            if (target < 0.1 && t - cell.lastFlip > 2000) {
                const flipChance = 0.4 / 60; // per frame (60fps)
                if (Math.random() < flipChance) {
                    cell.bit = 1 - cell.bit;
                    cell.flipStart = t;
                    cell.flipProgress = 0;
                    cell.lastFlip = t;
                }
            }
            
            if (cell.flipProgress < 1) {
                cell.flipProgress = Math.min(1, (t - cell.flipStart) / FLIP_MS);
            }

            // dim baseline - reduced to 0.4 (20% less opacity)
            const dimAlpha = 0.4;
            const b = cell.brightness;

            // base dim render (always visible at low alpha)
            if (b < 0.02) {
                ctx.fillStyle = `rgba(139,144,160,${dimAlpha})`;
                ctx.fillText(cell.bit, cell.x, cell.y);
                continue;
            }

            // color mix: dim gray -> vibrant accent
            const accent = cell.green
                ? [40, 255, 150]   // Much brighter, saturated green
                : [150, 200, 255]; // Much brighter, saturated blue

            const gray = [139, 144, 160];
            
            // Ramp up color transition faster
            const colorRamp = Math.min(1.0, b * 2.0);
            
            const r = Math.round(gray[0] + (accent[0] - gray[0]) * colorRamp);
            const g = Math.round(gray[1] + (accent[1] - gray[1]) * colorRamp);
            const bl = Math.round(gray[2] + (accent[2] - gray[2]) * colorRamp);
            
            // Ramp up opacity faster
            const alpha = Math.min(1.0, dimAlpha + (2.5 * b));

            // flip scaleY animation
            const scale = Math.abs(Math.cos(cell.flipProgress * Math.PI));
            ctx.save();
            ctx.translate(cell.x, cell.y);
            ctx.scale(1, Math.max(0.05, scale));
            
            ctx.fillStyle = `rgba(${r},${g},${bl},${alpha})`;
            ctx.fillText(cell.bit, 0, 0);
            ctx.restore();
        }

        requestAnimationFrame(draw);
    }

    window.addEventListener('mousemove', (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY + window.scrollY;
        mouse.active = true;
    }, { passive: true });

    window.addEventListener('mouseleave', () => { mouse.active = false; });

    window.addEventListener('touchmove', (e) => {
        if (e.touches[0]) {
            mouse.x = e.touches[0].clientX;
            mouse.y = e.touches[0].clientY + window.scrollY;
            mouse.active = true;
        }
    }, { passive: true });
    window.addEventListener('touchend', () => { mouse.active = false; });

    let rT;
    window.addEventListener('resize', () => {
        clearTimeout(rT);
        rT = setTimeout(resize, 120);
    });

    // Observe document height changes
    const resizeObserver = new ResizeObserver(() => {
        clearTimeout(rT);
        rT = setTimeout(resize, 120);
    });
    resizeObserver.observe(document.body);

    resize();
    // Re-resize after content loads
    window.addEventListener('load', () => setTimeout(resize, 100));
    requestAnimationFrame(draw);
})();
