'use strict';

(function () {
    const OVERLAY_ID = 'global-page-loader';
    const MESSAGE_ID = 'global-page-loader-message';
    const STYLE_ID = 'global-page-loader-style';
    const ACTIVE_CLASS = 'global-loader-active';
    const DEFAULT_MESSAGE = '콘텐츠를 불러오는 중입니다...';
    const DEFAULT_MEDIA_SELECTOR = 'img,video,iframe';

    let overlayEl = null;
    let messageEl = null;

    function injectStyles() {
        if (document.getElementById(STYLE_ID)) {
            return;
        }
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
            html.${ACTIVE_CLASS}, html.${ACTIVE_CLASS} body {
                overflow: hidden;
            }

            #${OVERLAY_ID} {
                position: fixed;
                inset: 0;
                display: none;
                align-items: center;
                justify-content: center;
                background: rgba(255, 255, 255, 0.94);
                backdrop-filter: blur(2px);
                z-index: 9999;
                transition: opacity 0.2s ease;
                opacity: 0;
            }

            #${OVERLAY_ID}.visible {
                opacity: 1;
            }

            #${OVERLAY_ID} .global-page-loader__content {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 14px;
                text-align: center;
                padding: 30px 40px;
                border-radius: 16px;
                background-color: rgba(255, 255, 255, 0.9);
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
            }

            #${OVERLAY_ID} .global-page-loader__spinner {
                width: 44px;
                height: 44px;
                border-radius: 50%;
                border: 4px solid #dfe6ec;
                border-top-color: #3498db;
                animation: global-page-loader-spin 0.8s linear infinite;
            }

            #${OVERLAY_ID} .global-page-loader__message {
                font-size: 16px;
                color: #2c3e50;
                margin: 0;
                font-weight: 600;
                line-height: 1.4;
            }

            @keyframes global-page-loader-spin {
                from {
                    transform: rotate(0deg);
                }
                to {
                    transform: rotate(360deg);
                }
            }
        `;
        (document.head || document.documentElement).appendChild(style);
    }

    function attachOverlay() {
        injectStyles();
        if (overlayEl) {
            return overlayEl;
        }

        overlayEl = document.createElement('div');
        overlayEl.id = OVERLAY_ID;
        overlayEl.setAttribute('role', 'status');
        overlayEl.setAttribute('aria-live', 'polite');
        overlayEl.innerHTML = `
            <div class="global-page-loader__content">
                <div class="global-page-loader__spinner" aria-hidden="true"></div>
                <p id="${MESSAGE_ID}" class="global-page-loader__message">${DEFAULT_MESSAGE}</p>
            </div>
        `;
        overlayEl.style.display = 'none';

        const parent = document.body || document.documentElement;
        parent.appendChild(overlayEl);

        if (!document.body) {
            document.addEventListener(
                'DOMContentLoaded',
                () => {
                    if (overlayEl && overlayEl.parentNode !== document.body) {
                        document.body.appendChild(overlayEl);
                    }
                },
                { once: true }
            );
        }

        messageEl = overlayEl.querySelector(`#${MESSAGE_ID}`);
        return overlayEl;
    }

    function ensureOverlay() {
        return overlayEl || attachOverlay();
    }

    function setMessage(message) {
        ensureOverlay();
        if (!messageEl) {
            messageEl = document.getElementById(MESSAGE_ID);
        }
        if (messageEl) {
            messageEl.textContent = message || DEFAULT_MESSAGE;
        }
    }

    function show(message) {
        const element = ensureOverlay();
        if (message) {
            setMessage(message);
        }
        element.style.display = 'flex';
        requestAnimationFrame(() => {
            element.classList.add('visible');
        });
        document.documentElement.classList.add(ACTIVE_CLASS);
    }

    function hide() {
        if (!overlayEl) {
            document.documentElement.classList.remove(ACTIVE_CLASS);
            return;
        }
        overlayEl.classList.remove('visible');
        const target = overlayEl;
        setTimeout(() => {
            if (!target.classList.contains('visible')) {
                target.style.display = 'none';
            }
        }, 220);
        document.documentElement.classList.remove(ACTIVE_CLASS);
    }

    function waitForSingleElement(el, timeout = 15000) {
        return new Promise(resolve => {
            if (!el) {
                resolve();
                return;
            }

            const tag = (el.tagName || '').toLowerCase();
            let settled = false;
            const cleanup = () => {
                if (el && el.removeEventListener) {
                    el.removeEventListener('load', finish);
                    el.removeEventListener('error', finish);
                    el.removeEventListener('loadeddata', finish);
                    el.removeEventListener('canplaythrough', finish);
                    el.removeEventListener('canplay', finish);
                }
            };

            const finish = () => {
                if (settled) {
                    return;
                }
                settled = true;
                cleanup();
                resolve();
            };

            const timerId = setTimeout(finish, timeout);
            const finishAndClear = () => {
                clearTimeout(timerId);
                finish();
            };

            switch (tag) {
                case 'img':
                    if (el.complete && el.naturalWidth > 0) {
                        finishAndClear();
                        return;
                    }
                    el.addEventListener('load', finishAndClear, { once: true });
                    el.addEventListener('error', finishAndClear, { once: true });
                    break;
                case 'video':
                case 'audio':
                    if (el.readyState >= 2) {
                        finishAndClear();
                        return;
                    }
                    el.addEventListener('loadeddata', finishAndClear, { once: true });
                    el.addEventListener('canplay', finishAndClear, { once: true });
                    el.addEventListener('canplaythrough', finishAndClear, { once: true });
                    el.addEventListener('error', finishAndClear, { once: true });
                    break;
                case 'iframe':
                    try {
                        const doc = el.contentDocument || el.contentWindow?.document;
                        if (doc && doc.readyState === 'complete') {
                            finishAndClear();
                            return;
                        }
                    } catch (error) {
                        // cross-origin, fall back to load
                    }
                    el.addEventListener('load', finishAndClear, { once: true });
                    el.addEventListener('error', finishAndClear, { once: true });
                    break;
                default:
                    finishAndClear();
                    break;
            }
        });
    }

    function collectMediaTargets(target, selector) {
        if (!target) {
            return [];
        }
        if (typeof target === 'string') {
            return Array.from(document.querySelectorAll(target));
        }
        if (target instanceof Element) {
            return Array.from(target.querySelectorAll(selector));
        }
        if (target instanceof Document) {
            return Array.from(target.querySelectorAll(selector));
        }
        if (target instanceof NodeList || Array.isArray(target)) {
            return Array.from(target).filter(Boolean);
        }
        return [];
    }

    function waitForMedia(target, options = {}) {
        const { selector = DEFAULT_MEDIA_SELECTOR, timeout = 15000 } = options;
        let elements = [];

        if (target instanceof Element || target instanceof Document) {
            elements = collectMediaTargets(target, selector);
        } else if (typeof target === 'string') {
            elements = collectMediaTargets(target, selector);
        } else if (target instanceof NodeList || Array.isArray(target)) {
            elements = collectMediaTargets(target, selector);
        } else if (!target) {
            elements = collectMediaTargets(document, selector);
        }

        if (elements.length === 0) {
            return Promise.resolve();
        }

        return Promise.all(elements.map(el => waitForSingleElement(el, timeout))).then(() => undefined);
    }

    function waitForFrameMedia(frameEl, options = {}) {
        if (!frameEl) {
            return Promise.resolve();
        }
        const { selector = 'video,img,canvas', timeout = 15000 } = options;

        try {
            const frameDoc = frameEl.contentDocument || frameEl.contentWindow?.document;
            if (!frameDoc) {
                return Promise.resolve();
            }
            const targets = collectMediaTargets(frameDoc, selector);
            if (targets.length === 0) {
                return Promise.resolve();
            }
            return Promise.all(targets.map(el => waitForSingleElement(el, timeout))).then(() => undefined);
        } catch (error) {
            // cross-origin frames cannot be inspected; resolve immediately
            return Promise.resolve();
        }
    }

    const api = {
        show,
        hide,
        setMessage,
        waitForMedia,
        waitForFrameMedia
    };

    ensureOverlay();
    show();

    window.PageLoader = api;
})();

