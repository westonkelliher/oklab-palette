import math

def oklab_to_linear_srgb(L, a, b):
    l_ = L + 0.3963377774*a + 0.2158037573*b
    m_ = L - 0.1055613458*a - 0.0638541728*b
    s_ = L - 0.0894841775*a - 1.2914855480*b
    l, m, s = l_**3, m_**3, s_**3
    R =  4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    G = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    B = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    return R, G, B

def linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return 12.92*c if c <= 0.0031308 else 1.055*(c**(1/2.4)) - 0.055

def in_gamut_lch(L, C, H, eps=1e-4):
    a = C*math.cos(math.radians(H)); b = C*math.sin(math.radians(H))
    R,G,B = oklab_to_linear_srgb(L,a,b)
    return all(-eps <= c <= 1+eps for c in (R,G,B))

def hex_lch(L, C, H):
    a = C*math.cos(math.radians(H)); b = C*math.sin(math.radians(H))
    rgb = [linear_to_srgb(c) for c in oklab_to_linear_srgb(L,a,b)]
    return "#{:02x}{:02x}{:02x}".format(*[round(255*c) for c in rgb])

HUES = [(i*60) % 360 for i in range(6)]   # 0, 60, 120, 180, 240, 300

def hues_n(n, offset=0):
    return [(offset + i*360/n) % 360 for i in range(n)]

# Generic: family is L^p * C^q = k. Given C, L = (k / C^q)^(1/p).
def c_range_for_k(k, hues, p, q, c_lo=0.001, c_hi=0.40, steps=4000,
                  l_min=0.35, l_max=0.92):
    valid_per_hue = []
    cs = [c_lo + (c_hi-c_lo)*i/(steps-1) for i in range(steps)]
    for H in hues:
        good = []
        for C in cs:
            ratio = k / (C**q)
            if ratio <= 0: continue
            L = ratio**(1.0/p)
            if l_min <= L <= l_max and in_gamut_lch(L, C, H):
                good.append(C)
        if not good: return None
        valid_per_hue.append((min(good), max(good)))
    lo = max(v[0] for v in valid_per_hue)
    hi = min(v[1] for v in valid_per_hue)
    if hi <= lo: return None
    return lo, hi

def build_grid(p, q, hues=HUES, n_levels=4, k_lo=0.0001, k_hi=0.20, steps=600,
               c_floor=0.0):
    best = None
    for i in range(1, steps):
        k = k_lo + (k_hi-k_lo)*i/steps
        r = c_range_for_k(k, hues, p, q)
        if r is None: continue
        Clo, Chi = max(r[0], c_floor), r[1]
        if Chi <= Clo: continue
        width = Chi - Clo
        if best is None or width > best[0]:
            best = (width, k, (Clo, Chi))
    width, k, (Clo, Chi) = best
    return build_grid_at_k(p, q, hues, n_levels, k, Clo, Chi)

def build_grid_at_k(p, q, hues, n_levels, k, Clo, Chi):
    if n_levels == 1:
        Cs = [(Clo+Chi)/2]
    else:
        Cs = [Clo + (Chi-Chi*0 + Chi - Clo)*0 + Clo + (Chi-Clo)*i/(n_levels-1) - Clo for i in range(n_levels)]
        Cs = [Clo + (Chi-Clo)*i/(n_levels-1) for i in range(n_levels)]
    rows = []
    for C in Cs:
        L = (k / (C**q))**(1.0/p)
        rows.append([(L, C, H, hex_lch(L,C,H)) for H in hues])
    return k, Clo, Chi, rows

def feasible_k_range(p, q, hues, c_floor, l_min=0.35, l_max=0.92,
                     k_lo=0.0001, k_hi=0.20, steps=2000):
    ks = []
    for i in range(1, steps):
        k = k_lo + (k_hi-k_lo)*i/steps
        r = c_range_for_k(k, hues, p, q, l_min=l_min, l_max=l_max)
        if r is None: continue
        Clo, Chi = max(r[0], c_floor), r[1]
        if Chi > Clo:
            ks.append((k, Clo, Chi))
    if not ks: return None
    return ks  # list of feasible (k, Clo, Chi)

def three_grids_across_k(p, q, hues, n_levels, c_floor, k_values):
    feas = feasible_k_range(p, q, hues, c_floor)
    if feas is None:
        raise RuntimeError("no feasible k")
    out = []
    for tk in k_values:
        k, Clo, Chi = min(feas, key=lambda e: abs(e[0]-tk))
        out.append(build_grid_at_k(p, q, hues, n_levels, k, Clo, Chi))
    return out

def grid_html(title, k, Clo, Chi, rows, ncols):
    cells = ""
    for row in rows:
        for L,C,H,h in row:
            cells += (f'<div class="sw" style="background:{h}">'
                      f'<span>L{L:.2f} C{C:.2f}<br>H{int(round(H))} {h}</span></div>')
    return (f'<section><h2>{title}</h2>'
            f'<div class="meta">k={k:.4f}, C∈[{Clo:.3f},{Chi:.3f}]</div>'
            f'<div class="grid" style="grid-template-columns:repeat({ncols},54px)">{cells}</div></section>')

k1, lo1, hi1, rows1 = build_grid(1, 1)
k2, lo2, hi2, rows2 = build_grid(2, 1)
k3, lo3, hi3, rows3 = build_grid(1, 2)
k4, lo4, hi4, rows4 = build_grid(3, 1)

# Tabs 2 & 3: 3 k values × 2 spreads, with C floor 0.035
C_FLOOR = 0.035
K_VALUES_L1 = [0.030, 0.045, 0.060]
K_VALUES_L2 = [0.015, 0.030, 0.045]
K_VALUES_L3 = [0.012, 0.020, 0.028]
C_FLOOR_2LVL = 0.055
spreadE = three_grids_across_k(1, 1, hues_n(10, 9), 2, C_FLOOR_2LVL, K_VALUES_L1)
spreadF = three_grids_across_k(1, 1, hues_n(7, 13),  3, C_FLOOR, K_VALUES_L1)
spreadA = three_grids_across_k(2, 1, hues_n(10, 9), 2, C_FLOOR_2LVL, K_VALUES_L2)
spreadB = three_grids_across_k(2, 1, hues_n(7, 13),  3, C_FLOOR, K_VALUES_L2)
spreadC = three_grids_across_k(3, 1, hues_n(10, 9), 2, C_FLOOR_2LVL, K_VALUES_L3)
spreadD = three_grids_across_k(3, 1, hues_n(7, 13),  3, C_FLOOR, K_VALUES_L3)

for label,(k,lo,hi,rows) in [("L·C",(k1,lo1,hi1,rows1)),
                              ("L²·C",(k2,lo2,hi2,rows2)),
                              ("L·C²",(k3,lo3,hi3,rows3)),
                              ("L³·C",(k4,lo4,hi4,rows4))]:
    print(f"{label} = {k:.4f}   C ∈ [{lo:.4f}, {hi:.4f}]")
for label,grids in [("L·C 10h×2", spreadE), ("L·C 7h×3", spreadF),
                     ("L²·C 10h×2", spreadA), ("L²·C 7h×3", spreadB),
                     ("L³·C 10h×2", spreadC), ("L³·C 7h×3", spreadD)]:
    for (k,lo,hi,rows) in grids:
        print(f"  {label} k={k:.4f}  C∈[{lo:.3f},{hi:.3f}]")

doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>oklab grids</title>
<style>
html,body{{margin:0;background:#000;color:#888;font-family:ui-monospace,monospace}}
.tabs{{display:flex;gap:4px;padding:12px 16px 0;border-bottom:1px solid #222}}
.tab{{background:#111;color:#888;border:1px solid #222;border-bottom:none;padding:6px 14px;cursor:pointer;font-family:inherit;font-size:12px;border-radius:6px 6px 0 0}}
.tab.active{{background:#222;color:#ddd}}
.wrap{{display:flex;gap:18px;padding:8px 16px;flex-wrap:wrap}}
.page{{display:none}}
.page.active{{display:block}}
.row{{padding:8px 0}}
.rowlabel{{padding:8px 16px 0;font-size:12px;color:#aaa}}
h2{{font-weight:400;font-size:13px;margin:0 0 4px}}
.meta{{font-size:11px;color:#666;margin-bottom:8px}}
.grid{{display:grid;gap:6px}}
.sw{{width:54px;height:54px;border-radius:4px;display:flex;align-items:flex-end;justify-content:center;padding:2px;font-size:7px;color:#000;box-sizing:border-box}}
.custom-controls{{display:flex;gap:14px;align-items:center;padding:12px 16px;flex-wrap:wrap;font-size:12px}}
.custom-controls label{{display:flex;flex-direction:column;gap:2px;color:#aaa}}
.custom-controls input{{width:80px;background:#111;color:#ddd;border:1px solid #333;padding:3px 5px;font-family:inherit;font-size:12px;border-radius:3px}}
.custom-controls button{{background:#222;color:#ddd;border:1px solid #444;padding:6px 12px;cursor:pointer;font-family:inherit;font-size:12px;border-radius:4px;align-self:flex-end}}
.custom-ls{{display:flex;gap:10px;padding:0 16px 8px;flex-wrap:wrap;font-size:12px;color:#aaa}}
.custom-ls label{{display:flex;flex-direction:column;gap:2px}}
.custom-ls input{{width:64px;background:#111;color:#ddd;border:1px solid #333;padding:3px 5px;font-family:inherit;font-size:12px;border-radius:3px}}
.sw span{{text-align:center;line-height:1.1}}
</style></head><body>
<div class="tabs">
  <button class="tab active" data-p="1">families</button>
  <button class="tab" data-p="4">L·C variations</button>
  <button class="tab" data-p="2">L²·C variations</button>
  <button class="tab" data-p="3">L³·C variations</button>
  <button class="tab" data-p="5">custom</button>
</div>
<div class="page active" id="p1"><div class="wrap">
{grid_html("L · C = k", k1, lo1, hi1, rows1, 6)}
{grid_html("L² · C = k", k2, lo2, hi2, rows2, 6)}
{grid_html("L³ · C = k", k4, lo4, hi4, rows4, 6)}
{grid_html("L · C² = k", k3, lo3, hi3, rows3, 6)}
</div></div>
<div class="page" id="p2">
<div class="row"><div class="rowlabel">L²·C — 10 hues × 2 levels</div><div class="wrap">
{grid_html(f"k = {spreadA[0][0]:.4f}", *spreadA[0], 10)}
{grid_html(f"k = {spreadA[1][0]:.4f}", *spreadA[1], 10)}
{grid_html(f"k = {spreadA[2][0]:.4f}", *spreadA[2], 10)}
</div></div>
<div class="row"><div class="rowlabel">L²·C — 7 hues × 3 levels</div><div class="wrap">
{grid_html(f"k = {spreadB[0][0]:.4f}", *spreadB[0], 7)}
{grid_html(f"k = {spreadB[1][0]:.4f}", *spreadB[1], 7)}
{grid_html(f"k = {spreadB[2][0]:.4f}", *spreadB[2], 7)}
</div></div>
</div>
<div class="page" id="p3">
<div class="row"><div class="rowlabel">L³·C — 10 hues × 2 levels</div><div class="wrap">
{grid_html(f"k = {spreadC[0][0]:.4f}", *spreadC[0], 10)}
{grid_html(f"k = {spreadC[1][0]:.4f}", *spreadC[1], 10)}
{grid_html(f"k = {spreadC[2][0]:.4f}", *spreadC[2], 10)}
</div></div>
<div class="row"><div class="rowlabel">L³·C — 7 hues × 3 levels</div><div class="wrap">
{grid_html(f"k = {spreadD[0][0]:.4f}", *spreadD[0], 7)}
{grid_html(f"k = {spreadD[1][0]:.4f}", *spreadD[1], 7)}
{grid_html(f"k = {spreadD[2][0]:.4f}", *spreadD[2], 7)}
</div></div>
</div>
<div class="page" id="p4">
<div class="row"><div class="rowlabel">L·C — 10 hues × 2 levels</div><div class="wrap">
{grid_html(f"k = {spreadE[0][0]:.4f}", *spreadE[0], 10)}
{grid_html(f"k = {spreadE[1][0]:.4f}", *spreadE[1], 10)}
{grid_html(f"k = {spreadE[2][0]:.4f}", *spreadE[2], 10)}
</div></div>
<div class="row"><div class="rowlabel">L·C — 7 hues × 3 levels</div><div class="wrap">
{grid_html(f"k = {spreadF[0][0]:.4f}", *spreadF[0], 7)}
{grid_html(f"k = {spreadF[1][0]:.4f}", *spreadF[1], 7)}
{grid_html(f"k = {spreadF[2][0]:.4f}", *spreadF[2], 7)}
</div></div>
</div>
<div class="page" id="p5">
  <div class="custom-controls">
    <label>hues <input type="number" id="cu_n" value="6" min="1" max="36" step="1"></label>
    <label>hue offset° <input type="number" id="cu_off" value="0" step="1"></label>
    <label>levels <input type="number" id="cu_lv" value="3" min="1" max="10" step="1"></label>
    <label>p (L exp) <input type="number" id="cu_p" value="2" step="0.5"></label>
    <label>q (C exp) <input type="number" id="cu_q" value="1" step="0.5"></label>
    <label>k <input type="number" id="cu_k" value="0.030" step="0.001"></label>
    <button id="cu_save">save JSON</button>
  </div>
  <div class="custom-ls" id="cu_ls"></div>
  <div class="wrap" id="cu_out"></div>
</div>
<script>
document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>{{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));
  t.classList.add('active');
  document.getElementById('p'+t.dataset.p).classList.add('active');
}}));

function oklabToLinearSRGB(L,a,b){{
  const l_=L+0.3963377774*a+0.2158037573*b;
  const m_=L-0.1055613458*a-0.0638541728*b;
  const s_=L-0.0894841775*a-1.2914855480*b;
  const l=l_**3,m=m_**3,s=s_**3;
  return [4.0767416621*l-3.3077115913*m+0.2309699292*s,
         -1.2684380046*l+2.6097574011*m-0.3413193965*s,
         -0.0041960863*l-0.7034186147*m+1.7076147010*s];
}}
function lin2srgb(c){{ c=Math.max(0,Math.min(1,c)); return c<=0.0031308?12.92*c:1.055*Math.pow(c,1/2.4)-0.055; }}
function inGamut(L,C,H){{
  const a=C*Math.cos(H*Math.PI/180), b=C*Math.sin(H*Math.PI/180);
  const r=oklabToLinearSRGB(L,a,b);
  return r.every(c=>c>=-1e-4 && c<=1+1e-4);
}}
function lchHex(L,C,H){{
  const a=C*Math.cos(H*Math.PI/180), b=C*Math.sin(H*Math.PI/180);
  const r=oklabToLinearSRGB(L,a,b).map(lin2srgb);
  return '#'+r.map(c=>Math.round(255*c).toString(16).padStart(2,'0')).join('');
}}

const defaultLs = n => {{
  if (n===1) return [0.7];
  const out=[]; for(let i=0;i<n;i++) out.push(+(0.9 - 0.5*i/(n-1)).toFixed(2));
  return out;
}};

function ensureLsInputs(){{
  const lv = parseInt(document.getElementById('cu_lv').value)||1;
  const wrap = document.getElementById('cu_ls');
  const existing = [...wrap.querySelectorAll('input')].map(i=>parseFloat(i.value));
  wrap.innerHTML='';
  const defs = defaultLs(lv);
  for (let i=0;i<lv;i++) {{
    const v = isFinite(existing[i]) ? existing[i] : defs[i];
    const lbl = document.createElement('label');
    lbl.innerHTML = `L${{i+1}} <input type="number" min="0" max="1" step="0.01" value="${{v}}">`;
    lbl.querySelector('input').addEventListener('input', render);
    wrap.appendChild(lbl);
  }}
}}

let lastPalette = null;
function render(){{
  ensureLsInputs.skip = true;
  const n   = parseInt(document.getElementById('cu_n').value)||1;
  const off = parseFloat(document.getElementById('cu_off').value)||0;
  const p   = parseFloat(document.getElementById('cu_p').value)||1;
  const q   = parseFloat(document.getElementById('cu_q').value)||1;
  const k   = parseFloat(document.getElementById('cu_k').value)||0;
  const lv  = parseInt(document.getElementById('cu_lv').value)||1;
  const Ls  = [...document.querySelectorAll('#cu_ls input')].map(i=>parseFloat(i.value));
  const hues = []; for(let i=0;i<n;i++) hues.push((off + i*360/n) % 360);
  const out = document.getElementById('cu_out');
  let html = '<section><div class="grid" style="grid-template-columns:repeat('+n+',54px)">';
  const colors = [];
  for (let li=0; li<lv; li++) {{
    const L = Ls[li];
    const C = Math.pow(k / Math.pow(L, p), 1/q);
    for (const H of hues) {{
      const ok = isFinite(C) && C>=0 && inGamut(L, C, H);
      const hex = ok ? lchHex(L, C, H) : '#222';
      colors.push({{L, C, H, hex, in_gamut: ok}});
      html += `<div class="sw" style="background:${{hex}}"><span>L${{L.toFixed(2)}}<br>C${{(C||0).toFixed(3)}}<br>H${{Math.round(H)}}</span></div>`;
    }}
  }}
  html += '</div></section>';
  out.innerHTML = html;
  lastPalette = {{ equation: `L^${{p}} * C^${{q}} = k`, p, q, k, hues, lightness_levels: Ls, colors }};
}}

document.getElementById('cu_n').addEventListener('input', render);
document.getElementById('cu_off').addEventListener('input', render);
document.getElementById('cu_p').addEventListener('input', render);
document.getElementById('cu_q').addEventListener('input', render);
document.getElementById('cu_k').addEventListener('input', render);
document.getElementById('cu_lv').addEventListener('input', ()=>{{ ensureLsInputs(); render(); }});
document.getElementById('cu_save').addEventListener('click', ()=>{{
  if(!lastPalette) return;
  const blob = new Blob([JSON.stringify(lastPalette, null, 2)], {{type:'application/json'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const stamp = new Date().toISOString().replace(/[:.]/g,'-').slice(0,19);
  a.href = url; a.download = `palette-${{stamp}}.json`;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}});

ensureLsInputs(); render();
</script>
</body></html>"""

with open("/home/weston/responses/oklab-lc-const.html","w") as f:
    f.write(doc)
print("wrote /home/weston/responses/oklab-lc-const.html")
