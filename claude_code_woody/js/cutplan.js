/* ============================================================
   cutplan.js — kapoptimering. Givet defektkartan längs brädan
   (5,4 m) väljer en DP var brädan ska kapas i tillåtna längder
   för att maximera totalt värde. Defekter sänker bitens kvalitet
   (A/B/C) eller klipps bort som spill (R).
   ============================================================ */
(function () {
  const L_M = 5.4;                 // brädlängd (m)
  const CM = Math.round(L_M * 100);

  // klass -> svårighetsgrad (0 frisk .. 3 allvarlig)
  const SEV = { 1: 1, 3: 1, 4: 2, 2: 3, 5: 3, 6: 3 };
  // klass -> defektens utbredning längs brädan (cm)
  const FOOT = { 1: 9, 2: 32, 3: 38, 4: 75, 5: 42, 6: 7 };
  // svårighet -> kvalitet (alla säljbara; snitten placeras för max A/B)
  const GRADE = ["A", "B", "C", "C"];

  // kr/m per kvalitet
  const PRICE = { A: 58, B: 40, C: 24 };
  const COLOR = { A: "#4aa86a", B: "#d6a23e", C: "#cf6b46" };

  function plan(features, lengths) {
    const lens = (lengths || [3.0, 2.7, 2.4]).slice().sort((a, b) => b - a);
    const lenCm = lens.map(l => Math.round(l * 100));

    // svårighetsprofil längs brädan
    const sev = new Float32Array(CM);
    for (const f of features) {
      const s = SEV[f.cls] || 0; if (!s) continue;
      const c = Math.round(f.u * CM), r = Math.round((FOOT[f.cls] || 10) / 2);
      for (let i = Math.max(0, c - r); i < Math.min(CM, c + r); i++) if (s > sev[i]) sev[i] = s;
    }
    const gradeOf = (a, b) => { let w = 0; for (let i = a; i < b; i++) if (sev[i] > w) w = sev[i]; return GRADE[w]; };

    // DP: best[i] = max värde av första i cm
    const best = new Float64Array(CM + 1);
    const choice = new Array(CM + 1).fill(null);
    for (let i = 1; i <= CM; i++) {
      best[i] = best[i - 1]; choice[i] = { trim: true };        // kapa bort 1 cm spill
      for (const lc of lenCm) {
        if (i - lc < 0) continue;
        const g = gradeOf(i - lc, i);
        const v = best[i - lc] + PRICE[g] * (lc / 100);
        if (v > best[i] + 1e-9) { best[i] = v; choice[i] = { a: i - lc, b: i, g }; }
      }
    }
    // backtrack
    const pieces = []; let i = CM;
    while (i > 0) {
      const c = choice[i];
      if (!c) break;
      if (c.trim) i -= 1;
      else { pieces.push(c); i = c.a; }
    }
    pieces.reverse();

    let used = 0;
    const out = pieces.map(p => {
      const len = (p.b - p.a) / 100;
      used += (p.b - p.a);
      return {
        aU: p.a / CM, bU: p.b / CM, lenM: len, grade: p.g,
        value: Math.round(PRICE[p.g] * len), color: COLOR[p.g],
      };
    });
    return {
      pieces: out,
      totalValue: Math.round(best[CM]),
      yield: used / CM,
      trimM: (CM - used) / 100,
      L: L_M, lengths: lens,
    };
  }

  window.CutPlan = { plan, PRICE, COLOR, GRADE, L: L_M };
})();
