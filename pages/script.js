/* MemU-Bench project page */
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ------------------------------------------------------------ nav scroll-spy */
(() => {
  const links = [...document.querySelectorAll('.mb-nav nav a[href^="#"]')];
  const spy = new IntersectionObserver(
    (entries) =>
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        links.forEach((a) => a.classList.toggle("is-active", a.getAttribute("href") === `#${e.target.id}`));
      }),
    { rootMargin: "-45% 0px -50% 0px" },
  );
  links.forEach((a) => {
    const el = document.querySelector(a.getAttribute("href"));
    if (el) spy.observe(el);
  });
})();

/* ------------------------------------------------------------ task explorer */
(() => {
  const box = document.querySelector("[data-mb-explorer]");
  if (!box) return;
  // Text from android_world/task_evals/fixed_tasks/*.py (goal / full_goal / information) and
  // human reference steps from eval_results/human.json.
  const tasks = [
    {
      id: "User0Short_ClockDeleteAlarm",
      name: "Delete an alarm",
      app: "clock",
      hist: "L1",
      human: 4,
      goal: 'Please delete the alarm <span class="mb-a">I just set</span>.',
      full: 'Please delete the alarm <span class="mb-r">for 14:00</span>',
      hint: "I just set an afternoon alarm.",
    },
    {
      id: "User0Short_ContactsAddContact",
      name: "Save a caller",
      app: "contacts",
      hist: "L1",
      human: 9,
      goal: 'Save <span class="mb-a">the first call this morning</span> as a contact named Courier in contacts app.',
      full: 'Save <span class="mb-r">the number 13811223344</span> as a contact named Courier in contacts app.',
      hint: "That person's phone number starts with 138.",
    },
    {
      id: "User0Short_CalendarAddEvent",
      name: "Schedule a picnic",
      app: "simple calendar",
      hist: "L1",
      human: 16,
      goal:
        'I plan to have a picnic at <span class="mb-a">the location I just marked on the map</span> from 2 p.m. to 6 p.m. the day after tomorrow. Please help me add this schedule to the simple calendar app.',
      full:
        'I plan to have a picnic at <span class="mb-r">Barstow</span> from 2 p.m. to 6 p.m. the day after tomorrow. Please help me add this schedule to the simple calendar app.',
      hint: "I marked a location on the OsmAnd app.",
    },
    {
      id: "User5Short_SmsSendExpenseToContact",
      name: "Report a total",
      app: "simple sms messenger",
      hist: "L1",
      human: 6,
      goal:
        'I calculated my total expenses. Please tell Mary Brown <span class="mb-a">how much I spent</span> via simple sms messenger app.',
      full: 'Send a text message to Mary Brown via simple sms messenger app, saying: <span class="mb-r">I spent 9000 yuan.</span>',
      hint: "I just calculated the amount with the calculator.",
    },
    {
      id: "User0Long_ClockSetAlarmBeforeFlight",
      name: "Alarm before a flight",
      app: "clock",
      hist: "L2",
      human: 5,
      goal: 'Set an alarm <span class="mb-a">2 hours before my flight</span> in clock app.',
      full: 'Set an alarm <span class="mb-r">for 7:00 PM today</span> in clock app.',
      hint: "Charles Martinez texted me via simple sms messenger app reminding me about the flight time.",
    },
    {
      id: "User1Long_RetroMusicPlayFavoriteSong",
      name: "Play a favorite song",
      app: "retro music",
      hist: "L2",
      human: 4,
      goal: 'Play <span class="mb-a">my favorite song</span> in retro music app.',
      full: 'Play <span class="mb-r">Moments</span> in retro music app.',
      hint: "I don't remember the song name, but I texted David Johnson via simple sms messenger app about my favorite song.",
    },
    {
      id: "User4Long_ExpenseRecordTravel",
      name: "Record a travel expense",
      app: "pro expense",
      hist: "L2",
      human: 8,
      goal:
        "Record my travel expense in pro expense app, name it 'Travel', category is 'social', the amount is <span class=\"mb-a\">around 1000 yuan which I calculated earlier using the calculator</span>.",
      full: "Record an expense in pro expense app named 'Travel' with amount <span class=\"mb-r\">1035 yuan</span> and category 'Social'.",
      hint: "The exact amount is 1035 yuan.",
    },
  ];
  const list = box.querySelector(".mb-tasklist");
  const meta = box.querySelector("[data-mb-meta]");
  const goal = box.querySelector("[data-mb-goal]");
  const full = box.querySelector("[data-mb-full]");
  const hint = box.querySelector("[data-mb-hint]");
  const buttons = tasks.map((t, k) => {
    const b = document.createElement("button");
    b.type = "button";
    b.setAttribute("role", "tab");
    const ab = t.app.split(" ").length > 1 ? t.app.split(" ").map((w) => w[0]).join("").slice(0, 2) : t.app.slice(0, 2);
    b.innerHTML = `<span class="mb-ticon">${ab.toUpperCase()}</span><b>${t.name}</b><small>${t.hist} · ${t.app}</small>`;
    b.addEventListener("click", () => show(k));
    list.append(b);
    return b;
  });
  function show(k) {
    const t = tasks[k];
    buttons.forEach((b, i) => b.setAttribute("aria-selected", String(i === k)));
    meta.innerHTML =
      `<span class="mb-chip">${t.id}</span>` +
      `<span class="mb-chip mb-chip--teal">app · ${t.app}</span>` +
      `<span class="mb-chip mb-chip--violet">${t.hist === "L1" ? "Level-1 · shorter history" : "Level-2 · longer history"}</span>` +
      `<span class="mb-chip">human reference · ${t.human} steps</span>`;
    goal.innerHTML = t.goal;
    full.innerHTML = t.full;
    hint.innerHTML = `<b>What the user's history holds:</b> “${t.hint}”`;
  }
  show(2);
})();

/* ------------------------------------------------------------ app bars */
(() => {
  const ul = document.querySelector("[data-mb-appbars]");
  if (!ul) return;
  // app_name of every task class in android_world/task_evals/fixed_tasks/ (118 tasks);
  // "simple gallery" includes one task declared as "simple gallery pro".
  const apps = [
    ["simple sms messenger", 22],
    ["tasks", 14],
    ["simple calendar", 11],
    ["pro expense", 11],
    ["broccoli (recipes)", 9],
    ["simple gallery", 7],
    ["clock", 6],
    ["contacts", 6],
    ["joplin", 6],
    ["taodian", 6],
    ["phone", 5],
    ["chilemei", 4],
    ["retro music", 4],
    ["jingdian", 3],
    ["tuantuanwaimai", 2],
    ["files", 1],
    ["solitairecg", 1],
  ];
  ul.innerHTML = apps
    .map(([name, n]) => `<li><span title="${name}">${name}</span><i style="--n: ${n}"></i><b>${n}</b></li>`)
    .join("");
})();

/* ------------------------------------------------------------ results (Table 2) */
(() => {
  const box = document.querySelector("[data-mb-results]");
  if (!box) return;
  const table = box.querySelector("[data-mb-table]");
  const note = box.querySelector("[data-mb-resnote]");
  // Table 2 of the paper: [L1 SR, L1 SPL, L2 SR, L2 SPL, Avg IE, Avg SR, Avg SPL] for Vanilla / w/ Summary / w/ AppMem.
  const groups = [
    [
      "Closed-source models",
      [
        ["Gemini-3.1-Pro", [26.8, 18.1, 23.4, 14.0, 0.65, 25.4, 16.4], [43.7, 34.7, 36.2, 27.2, 0.78, 40.7, 31.7], [64.8, 55.2, 63.8, 53.5, 0.85, 64.4, 54.5]],
        ["GPT-5.5", [28.1, 18.1, 17.0, 11.9, 0.66, 23.7, 15.7], [73.2, 63.7, 57.5, 48.2, 0.86, 67.0, 57.6], [74.7, 68.1, 72.3, 64.9, 0.91, 73.7, 66.9]],
        ["Claude-Opus-4.8", [16.9, 14.7, 19.2, 13.4, 0.8, 17.8, 14.2], [57.8, 50.3, 44.7, 37.6, 0.86, 52.5, 45.3], [56.3, 49.7, 53.2, 47.8, 0.89, 55.1, 49.0]],
      ],
    ],
    [
      "Open-source models",
      [
        ["Qwen3.5-397B-A17B", [18.3, 13.3, 6.4, 4.3, 0.72, 13.6, 9.7], [40.9, 35.1, 27.7, 20.4, 0.82, 35.6, 29.3], [56.3, 50.5, 46.8, 41.9, 0.9, 52.5, 47.1]],
        ["Qwen3-VL-32B", [2.8, 1.5, 2.1, 0.6, 0.45, 2.5, 1.2], [9.9, 7.6, 8.5, 5.8, 0.74, 9.3, 6.9], [18.3, 15.5, 14.9, 12.7, 0.85, 17.0, 14.4]],
        ["Qwen3-VL-8B", [4.2, 3.1, 4.3, 2.2, 0.64, 4.2, 2.7], [15.5, 11.7, 2.1, 1.1, 0.73, 10.2, 7.5], [18.3, 13.9, 8.5, 6.3, 0.76, 14.4, 10.9]],
      ],
    ],
    [
      "End-to-end GUI agents",
      [
        ["UI-Venus-1.5-8B", [1.4, 1.4, 2.1, 0.7, 0.67, 1.7, 1.1], [2.8, 0.9, 0.0, 0.0, 0.3, 1.7, 0.5], [11.3, 8.6, 12.8, 8.7, 0.72, 11.9, 8.6]],
        ["MAI-UI-8B", [5.6, 4.2, 4.3, 2.2, 0.67, 5.1, 3.4], [7.0, 5.3, 6.4, 3.2, 0.65, 6.8, 4.4], [21.1, 15.8, 23.4, 16.9, 0.74, 22.0, 16.2]],
        ["GUI-Owl-1.5-8B", [2.8, 2.5, 2.1, 0.5, 0.67, 2.5, 1.7], [4.2, 1.4, 4.3, 1.0, 0.3, 4.2, 1.3], [5.6, 3.8, 10.6, 5.0, 0.56, 7.6, 4.3]],
      ],
    ],
  ];
  const settings = ["Vanilla", "w/ Summary", "w/ AppMem"];
  const col = { sr: 5, spl: 6, ie: 4 };
  const fmt = (v, ie) => (ie ? v.toFixed(2) : v.toFixed(1));
  const notes = {
    spl: "Average SPL: success discounted by extra steps against the human reference.",
    sr: "Average success rate over the 118 tasks.",
    ie: "Average IE over successful tasks only: 1.00 means human-like step economy.",
    gap: "δ = SPL on Level-1 minus SPL on Level-2. A large δ means performance collapses as the history grows; closer to 0 is better.",
    full: "All columns of Table 2: per-level SR and SPL, then the averages.",
  };

  function bars(metric) {
    const ie = metric === "ie";
    const max = ie ? 1 : metric === "gap" ? 20 : 80;
    const value = (row) => (metric === "gap" ? +(row[1] - row[3]).toFixed(1) : row[col[metric]]);
    let html = `<thead><tr><th scope="col">Backbone</th>${settings
      .map((s, i) => `<th scope="col" class="${i === 2 ? "is-ours" : ""}">${s}</th>`)
      .join("")}</tr></thead><tbody>`;
    groups.forEach(([gname, rows]) => {
      html += `<tr class="mb-group"><th colspan="4" scope="rowgroup">${gname}</th></tr>`;
      rows.forEach(([name, ...runs]) => {
        const vals = runs.map(value);
        const best = metric === "gap" ? Math.min(...vals.map(Math.abs)) : Math.max(...vals);
        html += `<tr><th scope="row">${name}</th>`;
        vals.forEach((v, i) => {
          const isBest = metric === "gap" ? Math.abs(v) === best : v === best;
          let delta = "";
          if (i > 0 && metric !== "gap") {
            const d = +(v - vals[0]).toFixed(2);
            if (d > 0) delta = `<small>+${fmt(d, ie)}</small>`;
          }
          const w = Math.max(0, Math.min(1, Math.abs(v) / max));
          html += `<td class="${i === 2 ? "is-ours" : ""}"><span class="mb-cell"><span class="mb-v${isBest ? " is-best" : ""}">${fmt(v, ie)}</span>${delta || "<small></small>"}<i style="--w: ${w}"></i></span></td>`;
        });
        html += "</tr>";
      });
    });
    table.innerHTML = html + "</tbody>";
    table.className = `mb-table mb-table--bars${metric === "gap" ? " is-gap" : ""}`;
  }

  function full() {
    const heads = ["L1 SR", "L1 SPL", "L2 SR", "L2 SPL", "Avg IE", "Avg SR", "Avg SPL"];
    let html = `<thead><tr><th scope="col">Model</th>${heads.map((h) => `<th scope="col">${h}</th>`).join("")}</tr></thead><tbody>`;
    groups.forEach(([gname, rows]) => {
      html += `<tr class="mb-group"><th colspan="8" scope="rowgroup">${gname}</th></tr>`;
      rows.forEach(([name, ...runs]) => {
        const best = heads.map((_, c) => Math.max(...runs.map((r) => r[c])));
        runs.forEach((r, i) => {
          html += `<tr class="${i === 0 ? "mb-first" : ""}${i === 2 ? " is-ours" : ""}"><th scope="row">${i === 0 ? name : `<span class="mb-sub-row">${settings[i]}</span>`}</th>`;
          r.forEach((v, c) => {
            html += `<td class="${v === best[c] ? "is-best" : ""}">${fmt(v, c === 4)}</td>`;
          });
          html += "</tr>";
        });
      });
    });
    table.innerHTML = html + "</tbody>";
    table.className = "mb-table mb-table--full";
  }

  const buttons = [...box.querySelectorAll(".mb-seg button")];
  function render(metric) {
    buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.metric === metric)));
    note.textContent = notes[metric];
    if (metric === "full") full();
    else bars(metric);
  }
  buttons.forEach((b) => b.addEventListener("click", () => render(b.dataset.metric)));
  render("spl");
})();

/* ------------------------------------------------------------ copy BibTeX */
(() => {
  function fallback(text) {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.append(area);
    area.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {
      ok = false;
    }
    area.remove();
    return ok;
  }
  async function copy(text) {
    if (navigator.clipboard?.writeText) {
      try {
        await Promise.race([
          navigator.clipboard.writeText(text),
          new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 800)),
        ]);
        return true;
      } catch {
        /* fall through */
      }
    }
    return fallback(text);
  }
  document.querySelectorAll("[data-copy]").forEach((button) =>
    button.addEventListener("click", async () => {
      const text = document.getElementById(button.dataset.copy).textContent;
      button.textContent = (await copy(text)) ? "Copied ✓" : "Select and copy";
      button.classList.add("is-done");
      setTimeout(() => {
        button.textContent = "Copy BibTeX";
        button.classList.remove("is-done");
      }, 1800);
    }),
  );
})();

/* ------------------------------------------------------------ animated figure */
(() => {
  const fig = document.querySelector("[data-mb-fig]");
  if (!fig) return;
  const stage = fig.querySelector("[data-mb-stage]");
  const wires = fig.querySelector("[data-mb-wires]");
  const tabs = [...fig.querySelectorAll(".mb-tabs button")];
  const caption = fig.querySelector("[data-mb-caption]");
  const playBtn = fig.querySelector("[data-mb-play]");
  const q = (s) => fig.querySelector(s);
  const qa = (s) => [...fig.querySelectorAll(s)];

  const film = q("[data-mb-film]");
  const filmPanel = q(".mb-p-film");
  const frames = qa(".mb-frame");
  const win = q(".mb-window");
  const winTag = q("[data-mb-wintag]");
  const phoneScreen = q("[data-mb-phone] .mb-dev-screen");
  const tap = q("[data-mb-tap]");
  const stepNo = q("[data-mb-stepno]");
  const actCode = q("[data-mb-act]");
  const osm = q("[data-mb-osm]");
  const osmState = q("[data-mb-osmstate]");
  const osmText = q("[data-mb-osmtext]");
  const keyApp = q("[data-mb-keyapp]");
  const amb = q(".mb-amb");

  /* ---------- helpers ---------- */
  const on = (key) => qa(`[data-step="${key}"]`).forEach((el) => el.classList.add("is-on"));
  const off = (key) => qa(`[data-step="${key}"]`).forEach((el) => el.classList.remove("is-on"));
  const screen = (name) =>
    qa("[data-screen]").forEach((el) => el.classList.toggle("is-shown", el.dataset.screen === name));
  const point = (fx, fy, fast) => {
    // tap at a fraction of the screen (used on the screenshot, whose fields are not DOM elements)
    if (fast) return;
    tap.style.left = `${fx * 100}%`;
    tap.style.top = `${fy * 100}%`;
    tap.classList.remove("is-tapping");
    void tap.offsetWidth;
    tap.classList.add("is-tapping");
  };
  const act = (n, text) => {
    stepNo.textContent = `#${n}`;
    actCode.textContent = text;
  };
  const visible = (el) => el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";

  function tapAt(el, fast) {
    if (fast || !el) return;
    const a = phoneScreen.getBoundingClientRect();
    const b = el.getBoundingClientRect();
    tap.style.left = `${b.left - a.left + b.width / 2}px`;
    tap.style.top = `${b.top - a.top + b.height / 2}px`;
    tap.classList.remove("is-tapping");
    void tap.offsetWidth;
    tap.classList.add("is-tapping");
  }

  let batch = 0;
  function placeWindow(b) {
    batch = b;
    const first = frames[b * 4];
    const last = frames[b * 4 + 3];
    if (!visible(film)) return;
    const p = filmPanel.getBoundingClientRect();
    const r1 = first.getBoundingClientRect();
    const r2 = last.getBoundingClientRect();
    const pad = 6;
    if (r2.top - r1.top > 4) {
      // frames wrapped onto two rows (narrow screens): frame the row
      win.style.left = `${r1.left - p.left - pad}px`;
      win.style.width = `${r2.right - r1.left + pad * 2}px`;
    } else {
      win.style.left = `${r1.left - p.left - pad}px`;
      win.style.width = `${r2.right - r1.left + pad * 2}px`;
    }
    win.style.top = `${r1.top - p.top - pad}px`;
    win.style.height = `${Math.max(r1.bottom, r2.bottom) - r1.top + pad * 2}px`;
  }

  /* one transient connector for the active step */
  let wireAnim = 0;
  function clearWire() {
    wireAnim++;
    wires.innerHTML = "";
  }
  function wire(a, b, mode, fast) {
    clearWire();
    if (fast || reduceMotion || innerWidth < 980 || !visible(a) || !visible(b)) return;
    const s = stage.getBoundingClientRect();
    const ra = a.getBoundingClientRect();
    const rb = b.getBoundingClientRect();
    let d;
    if (mode === "down") {
      const x1 = ra.left + ra.width / 2 - s.left;
      const y1 = ra.bottom - s.top;
      const x2 = rb.left + rb.width / 2 - s.left;
      const y2 = rb.top - s.top;
      const my = (y1 + y2) / 2;
      d = `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;
    } else if (rb.left + rb.width / 2 < ra.left + ra.width / 2) {
      // leftward: from the left edge of a to the right edge of b
      const x1 = ra.left - s.left;
      const y1 = ra.top + ra.height / 2 - s.top;
      const x2 = rb.right - s.left;
      const y2 = rb.top + Math.min(rb.height / 2, 120) - s.top;
      const mx = (x1 + x2) / 2;
      d = `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
    } else {
      const x1 = ra.right - s.left;
      const y1 = ra.top + ra.height / 2 - s.top;
      const x2 = rb.left - s.left;
      const y2 = rb.top + Math.min(rb.height / 2, 60) - s.top;
      const mx = (x1 + x2) / 2;
      d = `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
    }
    const ns = "http://www.w3.org/2000/svg";
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    path.setAttribute("class", "mb-wire");
    wires.append(path);
    const len = path.getTotalLength();
    path.style.strokeDasharray = `${len}`;
    path.style.strokeDashoffset = `${len}`;
    void path.getBoundingClientRect();
    path.style.strokeDashoffset = "0";
    const dot = document.createElementNS(ns, "circle");
    dot.setAttribute("r", "4");
    dot.setAttribute("class", "mb-wire-dot");
    wires.append(dot);
    const id = wireAnim;
    const t0 = performance.now();
    const step = (now) => {
      if (id !== wireAnim) return;
      const k = Math.min((now - t0) / 900, 1);
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      const pt = path.getPointAtLength(e * len);
      dot.setAttribute("cx", pt.x);
      dot.setAttribute("cy", pt.y);
      if (k < 1) requestAnimationFrame(step);
      else dot.style.opacity = "0.0";
    };
    requestAnimationFrame(step);
  }

  /* ---------- reset to the empty state ---------- */
  function reset() {
    qa("[data-step]").forEach((el) => el.classList.remove("is-on"));
    clearWire();
    screen("home");
    amb.classList.remove("is-done");
    osmState.textContent = "ongoing";
    osmState.classList.remove("is-fin");
    osmText.textContent = "Searched the map for Barstow and opened the result.";
    osm.classList.remove("is-picked");
    keyApp.classList.remove("is-key");
    winTag.textContent = "window 1";
    act(1, 'open_app("Calendar")');
    batch = 0;
  }

  /* ---------- phases: [duration ms, (fast, t) => void] ---------- */
  const phases = [
    {
      cap: "A vague instruction arrives. From the current screen alone, the agent cannot tell which location “I just marked on the map” refers to.",
      steps: [
        [350, () => on("phone")],
        [900, () => on("instr")],
        [1000, () => on("amb")],
        [1900, () => on("think")],
        [600, () => {}],
      ],
    },
    {
      cap: "MemU-Bench supplies the user's raw history: screenshots, actions and timestamps. Tasks are split into Level-1 and Level-2 by how long this history is.",
      steps: [
        [300, () => on("film")],
        [1700, () => on("fr")],
        [1500, () => on("buckets")],
        [600, () => {}],
      ],
    },
    {
      cap: "AppMem slides a window over the history and summarizes it into one entry per app. The newest entry of the same app is fetched: if it is still ongoing, the two are merged; if finished, a new entry is added.",
      steps: [
        [
          500,
          (fast) => {
            on("mem");
            placeWindow(0);
            winTag.textContent = "window 1";
            on("win");
          },
        ],
        [800, (fast) => wire(win, q(".mb-p-mem"), "down", fast)],
        [800, () => on("m0")],
        [1300, () => on("m1")],
        [
          1100,
          () => {
            placeWindow(1);
            winTag.textContent = "window 2";
          },
        ],
        [800, (fast) => wire(win, osm, "down", fast)],
        [
          1000,
          () => {
            osmText.textContent = "Searched the map for Barstow, then saved it as a marker.";
            osmState.textContent = "finished";
            osmState.classList.add("is-fin");
            on("merged");
          },
        ],
        [1500, () => on("m2")],
        [600, () => {}],
      ],
    },
    {
      cap: "App-guided retrieval: infer which app could know the marked location, read only that app's entries, filter them into the key information, and verify it is sufficient.",
      steps: [
        [300, () => on("ret")],
        [900, () => on("r0")],
        [800, () => keyApp.classList.add("is-key")],
        [
          700,
          (fast) => {
            osm.classList.add("is-picked");
            wire(osm, q(".mb-p-ret"), "side", fast);
          },
        ],
        [1000, () => on("r1")],
        [1200, () => on("r2")],
        [1500, () => on("r3")],
        [600, () => {}],
      ],
    },
    {
      cap: "The note is passed to the agent with the goal. “The location I just marked” becomes Barstow, and the agent fills in the event on the emulator.",
      steps: [
        [600, (fast) => wire(q(".mb-p-ret"), q("[data-mb-phone]"), "side", fast)],
        [
          1000,
          () => {
            amb.classList.add("is-done");
            on("resolved");
            off("think");
          },
        ],
        [
          900,
          (fast) => {
            on("act");
            act(1, 'open_app("Calendar")');
            tapAt(q("[data-mb-calicon] img"), fast);
          },
        ],
        [
          1000,
          () => {
            screen("cal");
            act(3, 'click("New event")');
          },
        ],
        [1000, (fast) => (act(4, 'type("Picnic")'), point(0.62, 0.2, fast))],
        [1000, (fast) => (act(6, 'type("Barstow")'), point(0.62, 0.29, fast))],
        [1000, (fast) => (act(10, "set date · day after tomorrow"), point(0.62, 0.38, fast))],
        [1000, (fast) => (act(15, "set time · 2:00 – 6:00 PM"), point(0.62, 0.465, fast))],
        [900, (fast) => (act(17, 'click("Save")'), point(0.5, 0.87, fast))],
        [
          1300,
          () => {
            on("saved");
            act(18, 'terminate("success")');
          },
        ],
        [600, () => {}],
      ],
    },
    {
      cap: "The episode is scored: a rule-based check reads the calendar's database, and the agent's step count is compared with a human's on the same task for IE and SPL.",
      steps: [
        [300, () => on("eval")],
        [700, (fast) => wire(q("[data-mb-phone]"), q(".mb-p-eval"), "side", fast)],
        [600, () => on("c0")],
        [500, () => on("c1")],
        [700, () => on("c2")],
        [1000, () => on("sr")],
        [800, () => on("b0")],
        [800, () => on("b1")],
        [1200, () => on("spl")],
        [2600, () => {}],
      ],
    },
  ];

  /* ---------- engine ---------- */
  let token = 0;
  let current = 0;
  let playing = !reduceMotion;
  let inView = false;
  let phaseDone = false;
  const CANCEL = Symbol("cancel");
  const wait = (ms, t) =>
    new Promise((res, rej) => setTimeout(() => (t === token ? res() : rej(CANCEL)), ms));

  function applyUpTo(k, inclusive) {
    fig.classList.add("is-instant");
    stage.dataset.phase = String(k);
    reset();
    const end = inclusive ? k : k - 1;
    for (let p = 0; p <= end; p++) phases[p].steps.forEach(([, fn]) => fn(true, token));
    void fig.offsetWidth;
    fig.classList.remove("is-instant");
  }

  function setTabs(k, running, total) {
    stage.dataset.phase = String(k);
    caption.textContent = phases[k].cap;
    tabs.forEach((b, i) => {
      b.setAttribute("aria-selected", String(i === k));
      b.classList.toggle("is-done", i < k);
      const bar = b.querySelector("i");
      bar.style.transition = "none";
      bar.style.transform = i < k ? "scaleX(1)" : "scaleX(0)";
      if (i === k) {
        void bar.offsetWidth;
        if (running) {
          bar.style.transition = `transform ${total}ms linear`;
          bar.style.transform = "scaleX(1)";
        } else {
          bar.style.transform = "scaleX(1)";
        }
      }
    });
  }

  async function run(k) {
    const t = ++token;
    current = k;
    phaseDone = false;
    applyUpTo(k, false);
    const total = phases[k].steps.reduce((s, [d]) => s + d, 0);
    setTabs(k, true, total);
    try {
      for (const [dur, fn] of phases[k].steps) {
        fn(false, t);
        await wait(dur, t);
      }
      phaseDone = true;
      if (!playing || !inView) return;
      await wait(k === phases.length - 1 ? 1200 : 500, t);
      run((k + 1) % phases.length);
    } catch (e) {
      if (e !== CANCEL) throw e;
    }
  }

  // show phase k fully drawn, without animation
  function showStatic(k) {
    token++;
    current = k;
    phaseDone = true;
    applyUpTo(k, true);
    setTabs(k, false, 0);
  }

  function setPlaying(p) {
    playing = p;
    fig.classList.toggle("is-paused", !p);
    playBtn.setAttribute("aria-label", p ? "Pause animation" : "Play animation");
  }

  tabs.forEach((b, k) =>
    b.addEventListener("click", () => {
      if (playing && !reduceMotion) run(k);
      else showStatic(k);
    }),
  );

  playBtn.addEventListener("click", () => {
    if (playing) {
      setPlaying(false);
      showStatic(current);
    } else {
      setPlaying(true);
      run(phaseDone ? (current + 1) % phases.length : current);
    }
  });

  if (reduceMotion) {
    fig.classList.add("is-static");
    setPlaying(false);
    showStatic(phases.length - 1);
  } else {
    reset();
    setTabs(0, false, 0);
    tabs[0].querySelector("i").style.transform = "scaleX(0)";
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          inView = e.isIntersecting;
          if (inView) {
            if (playing) run(phaseDone ? (current + 1) % phases.length : current);
          } else if (playing) {
            showStatic(current);
          }
        }),
      { threshold: 0.25 },
    );
    io.observe(fig);
  }

  /* keep the window and any connector aligned on resize */
  new ResizeObserver(() => {
    if (q('[data-step="win"]').classList.contains("is-on")) {
      const old = win.style.transition;
      win.style.transition = "none";
      placeWindow(batch);
      void win.offsetWidth;
      win.style.transition = old;
    }
    clearWire();
  }).observe(stage);
})();
