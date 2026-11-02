import React, { useEffect, useRef } from 'react';

const VERTEX_SHADER = `
  attribute vec2 aPosition;
  varying vec2 vUv;

  void main() {
    vUv = aPosition * 0.5 + 0.5;
    gl_Position = vec4(aPosition, 0.0, 1.0);
  }
`;

const FRAGMENT_SHADER = `
  precision highp float;

  uniform vec2 uResolution;
  uniform float uTime;
  uniform float uScale;
  uniform float uContrast;
  uniform float uSurge;

  varying vec2 vUv;

  vec3 permute(vec3 x) {
    return mod(((x * 34.0) + 1.0) * x, 289.0);
  }

  float snoise(vec2 v) {
    const vec4 C = vec4(
      0.211324865405187,
      0.366025403784439,
      -0.577350269189626,
      0.024390243902439
    );
    vec2 i = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod(i, 289.0);
    vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
    vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
    m = m * m;
    m = m * m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
    vec3 g;
    g.x = a0.x * x0.x + h.x * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
  }

  float fbm(vec2 st) {
    float value = 0.0;
    float amplitude = 0.5;
    for (int i = 0; i < 4; i++) {
      value += amplitude * snoise(st);
      st *= 2.0;
      amplitude *= 0.5;
    }
    return value;
  }

  void main() {
    vec2 st = gl_FragCoord.xy / uResolution.xy;
    st = (st - 0.5) * uScale + 0.5;
    st.x *= uResolution.x / max(1.0, uResolution.y);
    float time = uTime * 0.052;

    vec2 q = vec2(0.0);
    q.x = fbm(st + vec2(time));
    q.y = fbm(st + vec2(1.0));

    vec2 r = vec2(0.0);
    r.x = fbm(st + q + vec2(1.7, 9.2) + 0.12 * time);
    r.y = fbm(st + q + vec2(8.3, 2.8) + 0.095 * time);

    float f = fbm(st + r);

    // Pure Xundao / Variant smooth fluid wave formula, calibrated to warm Survey Atlas paper
    // with medium-sepia wave shadows (visible liquid waves, never black!)
    vec3 colorPaper = vec3(0.972, 0.950, 0.906); // #f8f2e7 warm cotton paper
    vec3 colorMist  = vec3(0.898, 0.862, 0.795); // #e5dcch soft parchment wave mist
    vec3 colorSlate = vec3(0.758, 0.706, 0.622); // #c1b49f distinct warm stone wave contour
    vec3 colorInk   = vec3(0.415, 0.365, 0.300); // #6a5d4d medium sepia-brown (visible depth, never black)

    vec3 color = mix(colorPaper, colorMist, clamp((f * f) * 3.0 * uContrast, 0.0, 1.0));
    float wash = clamp(length(r) * (0.16 * uContrast), 0.0, 1.0);
    color = mix(color, colorInk, wash);
    color = mix(color, colorSlate, clamp(length(q) * 0.62 * uContrast, 0.0, 1.0));
    float highlight = smoothstep(0.64, 0.98, f);
    color = mix(color, vec3(0.996, 0.990, 0.976), highlight * (0.38 * uContrast));

    gl_FragColor = vec4(color, 1.0);
  }
`;

function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

export function AtlasWaterBackground({
  className = 'atlas-water-background',
  position = 'fixed',
  speed = 1,
  scale = 0.95,
  contrast = 1.02,
  surge = false,
  maxDpr = 1.75,
  zIndex = 0,
}) {
  const hostRef = useRef(null);
  const surgeStartedAtRef = useRef(0);

  useEffect(() => {
    if (surge) {
      surgeStartedAtRef.current = performance.now();
    }
  }, [surge]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;

    const canvas = document.createElement('canvas');
    Object.assign(canvas.style, {
      display: 'block',
      width: '100%',
      height: '100%',
      inset: '0',
      position: 'absolute',
      pointerEvents: 'none',
    });

    const gl =
      canvas.getContext('webgl', {
        alpha: false,
        antialias: false,
        depth: false,
        stencil: false,
        powerPreference: 'low-power',
        preserveDrawingBuffer: false,
      }) ||
      canvas.getContext('experimental-webgl');

    if (!gl) {
      return undefined;
    }

    const vs = compileShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
    const fs = compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
    if (!vs || !fs) {
      if (vs) gl.deleteShader(vs);
      if (fs) gl.deleteShader(fs);
      return undefined;
    }

    const program = gl.createProgram();
    if (!program) {
      gl.deleteShader(vs);
      gl.deleteShader(fs);
      return undefined;
    }

    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      gl.deleteProgram(program);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
      return undefined;
    }

    host.appendChild(canvas);
    host.dataset.waterReady = 'webgl';

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
      gl.STATIC_DRAW
    );

    gl.useProgram(program);
    const posLoc = gl.getAttribLocation(program, 'aPosition');
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

    const uResolution = gl.getUniformLocation(program, 'uResolution');
    const uTime = gl.getUniformLocation(program, 'uTime');
    const uScale = gl.getUniformLocation(program, 'uScale');
    const uContrast = gl.getUniformLocation(program, 'uContrast');
    const uSurge = gl.getUniformLocation(program, 'uSurge');

    let timeValue = 3.65;
    let surgeValue = 0;
    let widthPx = 1;
    let heightPx = 1;

    let disposed = false;
    let animationFrame = 0;
    let isAnimating = false;
    let previousTime = performance.now();
    const motionQuery = window.matchMedia?.('(prefers-reduced-motion: reduce)');

    const render = () => {
      if (disposed) return;
      gl.useProgram(program);
      gl.uniform2f(uResolution, widthPx, heightPx);
      gl.uniform1f(uTime, timeValue);
      gl.uniform1f(uScale, Math.max(0.2, scale));
      gl.uniform1f(uContrast, Math.max(0, contrast));
      gl.uniform1f(uSurge, surgeValue);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    };

    const resize = () => {
      if (disposed) return;
      const cssWidth = Math.max(1, host.clientWidth || window.innerWidth || 1);
      const cssHeight = Math.max(1, host.clientHeight || window.innerHeight || 1);
      const dprLimit = Math.min(2, Math.max(1, maxDpr));
      const dpr = Math.min(window.devicePixelRatio || 1, dprLimit);
      widthPx = Math.max(1, Math.round(cssWidth * dpr));
      heightPx = Math.max(1, Math.round(cssHeight * dpr));
      if (canvas.width !== widthPx || canvas.height !== heightPx) {
        canvas.width = widthPx;
        canvas.height = heightPx;
        gl.viewport(0, 0, widthPx, heightPx);
      }
      render();
    };

    const animate = (now) => {
      if (disposed || !isAnimating) return;
      const deltaSeconds = Math.min(0.05, Math.max(0, (now - previousTime) / 1000));
      previousTime = now;
      timeValue += deltaSeconds * Math.max(0, speed);

      if (surgeStartedAtRef.current > 0) {
        const elapsed = (now - surgeStartedAtRef.current) / 1000;
        if (elapsed <= 0.9) {
          const progress = Math.max(0, elapsed / 0.9);
          surgeValue = (1 - Math.pow(1 - progress, 3)) * 0.36;
        } else if (elapsed <= 1.6) {
          surgeValue = 0.36;
        } else if (elapsed <= 3.8) {
          surgeValue = 0.36 * (1 - (elapsed - 1.6) / 2.2);
        } else {
          surgeValue = 0;
          surgeStartedAtRef.current = 0;
        }
      }

      render();
      animationFrame = window.requestAnimationFrame(animate);
    };

    const syncAnimationState = () => {
      const shouldAnimate = !motionQuery?.matches && !document.hidden && speed > 0;
      if (shouldAnimate === isAnimating) {
        if (!isAnimating) render();
        return;
      }
      isAnimating = shouldAnimate;
      window.cancelAnimationFrame(animationFrame);
      if (isAnimating) {
        previousTime = performance.now();
        animationFrame = window.requestAnimationFrame(animate);
      } else {
        render();
      }
    };

    const resizeObserver = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : null;
    resizeObserver?.observe(host);
    window.addEventListener('resize', resize, { passive: true });
    window.visualViewport?.addEventListener('resize', resize, { passive: true });
    document.addEventListener('visibilitychange', syncAnimationState);
    motionQuery?.addEventListener?.('change', syncAnimationState);

    resize();
    syncAnimationState();

    return () => {
      disposed = true;
      isAnimating = false;
      window.cancelAnimationFrame(animationFrame);
      resizeObserver?.disconnect();
      window.removeEventListener('resize', resize);
      window.visualViewport?.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', syncAnimationState);
      motionQuery?.removeEventListener?.('change', syncAnimationState);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
      canvas.remove();
    };
  }, [contrast, maxDpr, scale, speed]);

  return (
    <div
      ref={hostRef}
      aria-hidden="true"
      className={className}
      data-testid={position === 'fixed' ? 'atlas-water-background' : 'agent-water-background'}
      style={{
        background: '#f7f1e3',
        inset: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
        position,
        userSelect: 'none',
        zIndex,
      }}
    />
  );
}

export default AtlasWaterBackground;
