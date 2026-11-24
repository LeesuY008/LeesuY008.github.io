/* 모든 프로젝트·학습 자료 페이지 좌측 상단의 'G' 버튼 → 대표페이지(index.html)
   각 페이지에서 <script src="home-badge.js" defer></script> 로 불러온다.
   화면 위에 띄우면 페이지 제목·버튼을 가리므로, 페이지 맨 위에 얇은 줄을 넣고 그 왼쪽에 둔다. */
(function () {
  if (document.getElementById("g-home")) return;
  var css = document.createElement("style");
  css.textContent =
    "#g-bar{display:block;box-sizing:border-box;width:100%;padding:10px 12px 0;position:relative;z-index:2147483000;" +
    "flex:0 0 100%;grid-column:1/-1}" +
    "#g-home{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;" +
    "text-decoration:none;font:800 18px/1 -apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;" +
    "background:#1f2328;color:#fff;box-shadow:0 0 0 2px rgba(255,255,255,.85),0 2px 6px rgba(0,0,0,.3);transition:transform .15s,background .15s}" +
    "#g-home:hover{transform:scale(1.08);background:#3b5bdb}" +
    "#g-home:focus-visible{outline:3px solid #7c96ff;outline-offset:2px}" +
    "@media (prefers-color-scheme:dark){#g-home{background:#f2f3f5;color:#1f2328}#g-home:hover{background:#7c96ff;color:#fff}}" +
    "@media print{#g-bar{display:none}}";
  document.head.appendChild(css);
  var bar = document.createElement("div");
  bar.id = "g-bar";
  var a = document.createElement("a");
  a.id = "g-home";
  a.href = "index.html";
  a.textContent = "G";
  a.title = "대표페이지로";
  a.setAttribute("aria-label", "대표페이지로 이동");
  bar.appendChild(a);
  document.body.insertBefore(bar, document.body.firstChild);
})();
