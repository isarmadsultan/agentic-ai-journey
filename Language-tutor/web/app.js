const STORAGE_KEY = "language_tutor_state_v1";
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DEFAULT_LANGUAGES = [
  "English",
  "Spanish",
  "French",
  "German",
  "Italian",
  "Portuguese",
  "Russian",
  "Chinese (Mandarin)",
  "Japanese",
  "Korean",
  "Arabic",
  "Hindi",
  "Urdu"
];

const elements = {
  statusText: document.getElementById("status-text"),
  logoutBtn: document.getElementById("logout-btn"),
  accountForm: document.getElementById("account-form"),
  accountFeedback: document.getElementById("account-feedback"),
  loginForm: document.getElementById("login-form"),
  loginFeedback: document.getElementById("login-feedback"),
  navButtons: document.querySelectorAll(".nav-btn"),
  views: document.querySelectorAll("[data-view]"),
  availableLanguages: document.getElementById("available-languages"),
  enrollBtn: document.getElementById("enroll-btn"),
  languageFeedback: document.getElementById("language-feedback"),
  userLanguages: document.getElementById("user-languages"),
  vocabForm: document.getElementById("vocab-form"),
  vocabFeedback: document.getElementById("vocab-feedback"),
  vocabLanguage: document.getElementById("vocab-language"),
  vocabList: document.getElementById("vocab-list"),
  storyForm: document.getElementById("story-form"),
  storyFeedback: document.getElementById("story-feedback"),
  storyLanguage: document.getElementById("story-language"),
  storyTheme: document.getElementById("story-theme"),
  storyProf: document.getElementById("story-prof"),
  storyMax: document.getElementById("story-max"),
  storyVocabList: document.getElementById("story-vocab-list"),
  selectAll: document.getElementById("select-all"),
  clearAll: document.getElementById("clear-all"),
  vocabModeRadios: document.querySelectorAll("input[name=\"vocab-mode\"]"),
  storyOutput: document.getElementById("story-output"),
  saveStory: document.getElementById("save-story")
};

const state = loadState();

function loadState() {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw) {
    try {
      return JSON.parse(raw);
    } catch (err) {
      console.warn("Failed to parse saved state", err);
    }
  }
  return {
    users: [],
    currentUserId: null,
    languages: DEFAULT_LANGUAGES.map((name, index) => ({
      languageId: index + 1,
      name
    })),
    userLanguages: [],
    vocabulary: [],
    story: "",
    seq: {
      userId: 1,
      userLanguageId: 1,
      vocabId: 1
    }
  };
}

function saveState() {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function setActiveView(viewId) {
  elements.views.forEach((view) => {
    view.classList.toggle("hidden", view.id !== viewId);
  });
  elements.navButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.target === viewId);
  });
}

function isLoggedIn() {
  return Boolean(state.currentUserId);
}

function currentUser() {
  return state.users.find((user) => user.userId === state.currentUserId) || null;
}

function updateAuthUI() {
  const user = currentUser();
  if (user) {
    elements.statusText.textContent = `Logged in as ${user.name}`;
    elements.logoutBtn.style.display = "inline-flex";
  } else {
    elements.statusText.textContent = "Guest";
    elements.logoutBtn.style.display = "none";
  }

  elements.navButtons.forEach((btn) => {
    const requiresAuth = btn.dataset.auth === "true";
    btn.disabled = requiresAuth && !user;
  });
}

function showFeedback(target, message, isError = false) {
  target.textContent = message;
  target.style.color = isError ? "#ff8f8f" : "var(--muted)";
}

function parseCommaWords(raw) {
  const cleaned = raw.replace(/\n/g, ",");
  const parts = cleaned.split(",").map((part) => part.trim()).filter(Boolean);
  const seen = new Set();
  const unique = [];
  parts.forEach((word) => {
    const key = word.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(word);
    }
  });
  return unique;
}

function getCheckedVocabIds() {
  const boxes = elements.storyVocabList.querySelectorAll("input[type=\"checkbox\"]");
  return new Set([...boxes].filter((box) => box.checked).map((box) => Number(box.value)));
}

function clampMaxWords(maxWords) {
  if (!Number.isFinite(maxWords) || maxWords <= 0) {
    return 20;
  }
  return Math.min(maxWords, 40);
}

function handleCreateAccount(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const name = (form.get("name") || "").trim();
  const email = (form.get("email") || "").trim().toLowerCase();
  const password = form.get("password") || "";
  const confirm = form.get("confirm") || "";

  if (!name) {
    showFeedback(elements.accountFeedback, "Name is required.", true);
    return;
  }
  if (!EMAIL_PATTERN.test(email)) {
    showFeedback(elements.accountFeedback, "Please enter a valid email.", true);
    return;
  }
  if (password.length < 8) {
    showFeedback(elements.accountFeedback, "Password must be at least 8 characters.", true);
    return;
  }
  if (password !== confirm) {
    showFeedback(elements.accountFeedback, "Passwords do not match.", true);
    return;
  }

  if (state.users.some((user) => user.email === email)) {
    showFeedback(elements.accountFeedback, "This email is already registered.", true);
    return;
  }

  const user = {
    userId: state.seq.userId++,
    name,
    email,
    password
  };
  state.users.push(user);
  saveState();

  event.target.reset();
  showFeedback(elements.accountFeedback, "Account created. You can log in now.");
  setActiveView("view-login");
}

function handleLogin(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const email = (form.get("email") || "").trim().toLowerCase();
  const password = form.get("password") || "";

  const user = state.users.find((candidate) => candidate.email === email);
  if (!user || user.password !== password) {
    showFeedback(elements.loginFeedback, "Invalid email or password.", true);
    return;
  }

  state.currentUserId = user.userId;
  saveState();
  updateAuthUI();
  refreshLanguageViews();
  refreshVocabView();
  refreshStoryView();
  showFeedback(elements.loginFeedback, "Logged in successfully.");
  setActiveView("view-languages");
}

function handleLogout() {
  state.currentUserId = null;
  saveState();
  updateAuthUI();
  refreshLanguageViews();
  refreshVocabView();
  refreshStoryView();
  elements.storyOutput.textContent = "No story yet. Generate one.";
  setActiveView("view-login");
}

function handleNavClick(event) {
  const target = event.currentTarget.dataset.target;
  if (!target) return;
  setActiveView(target);
  if (target === "view-story") {
    refreshStoryVocabList();
    updateVocabPickerState();
  }
}

function getUserLanguages(userId) {
  return state.userLanguages
    .filter((entry) => entry.userId === userId)
    .map((entry) => {
      const language = state.languages.find((lang) => lang.languageId === entry.languageId);
      return {
        userLanguageId: entry.userLanguageId,
        languageId: entry.languageId,
        name: language ? language.name : "Unknown"
      };
    });
}

function refreshLanguageViews() {
  elements.availableLanguages.innerHTML = "";
  elements.userLanguages.innerHTML = "";
  elements.languageFeedback.textContent = "";

  if (!isLoggedIn()) {
    return;
  }

  const userId = state.currentUserId;
  const enrolled = getUserLanguages(userId);
  const enrolledIds = new Set(enrolled.map((entry) => entry.languageId));

  state.languages.forEach((lang) => {
    if (!enrolledIds.has(lang.languageId)) {
      const option = document.createElement("option");
      option.value = String(lang.languageId);
      option.textContent = lang.name;
      elements.availableLanguages.appendChild(option);
    }
  });

  if (!elements.availableLanguages.children.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "All languages enrolled";
    elements.availableLanguages.appendChild(option);
  }

  if (!enrolled.length) {
    const li = document.createElement("li");
    li.textContent = "No languages enrolled yet.";
    elements.userLanguages.appendChild(li);
  } else {
    enrolled.forEach((entry) => {
      const li = document.createElement("li");
      li.textContent = entry.name;
      elements.userLanguages.appendChild(li);
    });
  }

  populateLanguageSelects();
}

function populateLanguageSelects() {
  if (!isLoggedIn()) {
    elements.vocabLanguage.innerHTML = "";
    elements.storyLanguage.innerHTML = "";
    return;
  }

  const enrolled = getUserLanguages(state.currentUserId);
  elements.vocabLanguage.innerHTML = "";
  elements.storyLanguage.innerHTML = "";

  enrolled.forEach((entry) => {
    const option = document.createElement("option");
    option.value = String(entry.userLanguageId);
    option.textContent = entry.name;
    elements.vocabLanguage.appendChild(option.cloneNode(true));
    elements.storyLanguage.appendChild(option);
  });

  if (elements.vocabLanguage.options.length && !elements.vocabLanguage.value) {
    elements.vocabLanguage.value = elements.vocabLanguage.options[0].value;
  }
  if (elements.storyLanguage.options.length && !elements.storyLanguage.value) {
    elements.storyLanguage.value = elements.storyLanguage.options[0].value;
  }
}

function handleEnrollLanguage() {
  if (!isLoggedIn()) return;
  const selectedId = Number(elements.availableLanguages.value);
  if (!selectedId) {
    showFeedback(elements.languageFeedback, "No available language selected.", true);
    return;
  }

  const exists = state.userLanguages.some(
    (entry) => entry.userId === state.currentUserId && entry.languageId === selectedId
  );
  if (exists) {
    return;
  }

  state.userLanguages.push({
    userLanguageId: state.seq.userLanguageId++,
    userId: state.currentUserId,
    languageId: selectedId
  });
  saveState();
  showFeedback(elements.languageFeedback, "Language enrolled.");
  refreshLanguageViews();
  refreshVocabView();
  refreshStoryView();
}

function handleAddVocab(event) {
  event.preventDefault();
  if (!isLoggedIn()) return;

  const form = new FormData(event.target);
  const userLanguageId = Number(elements.vocabLanguage.value);
  const wordInput = (form.get("word") || "").trim();
  const meaning = (form.get("meaning") || "").trim();
  const proficiency = (form.get("proficiency") || "").trim();

  if (!userLanguageId) {
    showFeedback(elements.vocabFeedback, "Choose a language first.", true);
    return;
  }
  const words = parseCommaWords(wordInput);
  if (!words.length) {
    showFeedback(elements.vocabFeedback, "At least one word is required.", true);
    return;
  }

  words.forEach((word) => {
    state.vocabulary.push({
      vocabId: state.seq.vocabId++,
      userLanguageId,
      word,
      meaning: meaning || null,
      proficiency: proficiency || null,
      createdAt: new Date().toISOString()
    });
  });
  saveState();
  event.target.reset();
  showFeedback(
    elements.vocabFeedback,
    `Saved ${words.length} ${words.length === 1 ? "word" : "words"}.`
  );
  refreshVocabView();
  refreshStoryView();
}

function refreshVocabView() {
  elements.vocabList.innerHTML = "";
  if (!isLoggedIn()) return;

  const userLanguageId = Number(elements.vocabLanguage.value);
  if (!userLanguageId) {
    const li = document.createElement("li");
    li.textContent = "Select a language to see vocabulary.";
    elements.vocabList.appendChild(li);
    return;
  }

  const vocabItems = state.vocabulary.filter(
    (item) => item.userLanguageId === userLanguageId
  );

  if (!vocabItems.length) {
    const li = document.createElement("li");
    li.textContent = "No words saved yet.";
    elements.vocabList.appendChild(li);
    return;
  }

  vocabItems.forEach((item) => {
    const li = document.createElement("li");
    const meaning = item.meaning ? ` (${item.meaning})` : "";
    const prof = item.proficiency ? ` [${item.proficiency}]` : "";
    li.textContent = `${item.word}${meaning}${prof}`;
    elements.vocabList.appendChild(li);
  });

  refreshStoryVocabList();
}

function refreshStoryView() {
  if (!isLoggedIn()) return;
  if (!elements.storyLanguage.value) {
    const options = elements.storyLanguage.options;
    if (options.length) {
      elements.storyLanguage.value = options[0].value;
    }
  }
  refreshStoryVocabList();
  updateVocabPickerState();
}

function getVocabularyPool(userLanguageId, proficiency) {
  let items = state.vocabulary.filter((item) => item.userLanguageId === userLanguageId);
  if (proficiency && proficiency !== "any") {
    items = items.filter((item) => (item.proficiency || "").toLowerCase() === proficiency);
  }
  return items;
}

function sampleWords(items, maxWords) {
  if (items.length <= maxWords) {
    return items;
  }
  const shuffled = items.slice().sort(() => 0.5 - Math.random());
  return shuffled.slice(0, maxWords);
}

function chooseVocabularyByTheme(items, theme, maxWords) {
  const tokens = (theme || "")
    .toLowerCase()
    .match(/[a-z0-9]+/g);
  if (!tokens || !tokens.length) {
    return sampleWords(items, maxWords);
  }
  const matches = items.filter((item) => {
    const word = item.word.toLowerCase();
    const meaning = (item.meaning || "").toLowerCase();
    return tokens.some((token) => word.includes(token) || meaning.includes(token));
  });
  if (!matches.length) {
    return sampleWords(items, maxWords);
  }
  return sampleWords(matches, maxWords);
}

function getVocabMode() {
  const selected = [...elements.vocabModeRadios].find((radio) => radio.checked);
  return selected ? selected.value : "all";
}

function setVocabMode(mode) {
  elements.vocabModeRadios.forEach((radio) => {
    radio.checked = radio.value === mode;
  });
  updateVocabPickerState();
}

function updateVocabPickerState() {
  const mode = getVocabMode();
  const disabled = mode !== "manual";
  elements.storyVocabList.classList.toggle("disabled", disabled);
  const checkboxes = elements.storyVocabList.querySelectorAll("input[type=\"checkbox\"]");
  checkboxes.forEach((box) => {
    box.disabled = disabled;
  });
}

function refreshStoryVocabList() {
  if (!isLoggedIn()) return;

  const userLanguageId = Number(elements.storyLanguage.value);
  const previouslyChecked = getCheckedVocabIds();
  elements.storyVocabList.innerHTML = "";

  if (!userLanguageId) {
    const empty = document.createElement("div");
    empty.className = "vocab-meta";
    empty.textContent = "Select a language to see vocabulary.";
    elements.storyVocabList.appendChild(empty);
    return;
  }

  const prof = elements.storyProf.value;
  const items = getVocabularyPool(userLanguageId, prof);

  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "vocab-meta";
    empty.textContent = "No vocabulary available for this language.";
    elements.storyVocabList.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    const wrapper = document.createElement("label");
    wrapper.className = "vocab-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = String(item.vocabId);
    checkbox.checked = previouslyChecked.has(item.vocabId);

    const content = document.createElement("div");
    const meaning = item.meaning ? ` (${item.meaning})` : "";
    const profTag = item.proficiency ? ` [${item.proficiency}]` : "";
    content.textContent = `${item.word}${meaning}${profTag}`;

    wrapper.appendChild(checkbox);
    wrapper.appendChild(content);
    elements.storyVocabList.appendChild(wrapper);
  });

  updateVocabPickerState();
}

function handleSelectAll() {
  setVocabMode("manual");
  const boxes = elements.storyVocabList.querySelectorAll("input[type=\"checkbox\"]");
  boxes.forEach((box) => {
    box.checked = true;
  });
}

function handleClearAll() {
  setVocabMode("manual");
  const boxes = elements.storyVocabList.querySelectorAll("input[type=\"checkbox\"]");
  boxes.forEach((box) => {
    box.checked = false;
  });
}

function buildStory(languageName, vocabulary, userName, theme) {
  const words = vocabulary.map((item) => item.word);
  const highlighted = words.join(", ");
  const themeLine = theme ? `The theme was ${theme}.` : "The theme was hopeful and personal.";
  const intro = `${userName} opened the notebook labeled ${languageName} and traced the words: ${highlighted}. ${themeLine}`;
  const middle = [
    `The day started with a quiet walk, and each word unlocked a new scene that matched the theme.`,
    `At the market, the sounds of ${languageName} flowed around ${userName}, and the words felt alive.`,
    `A friend joined the journey, practicing each word out loud until the rhythm felt natural.`,
    `By sunset, the words stitched together into a story of discovery and calm confidence.`
  ];
  const outro = `Before sleeping, ${userName} wrote a short summary in English to lock the memory in place.`;
  const story = [intro, ...middle, outro].join(" ");

  const summary = `Summary: ${userName} practiced ${languageName} vocabulary with a theme of ${theme || "personal growth"}. The words felt natural after being used in a story.`;

  return `${story}\n\n${summary}`;
}

function handleGenerateStory(event) {
  event.preventDefault();
  if (!isLoggedIn()) return;

  const userLanguageId = Number(elements.storyLanguage.value);
  const prof = elements.storyProf.value;
  const maxWords = clampMaxWords(Number(elements.storyMax.value) || 20);
  const theme = elements.storyTheme.value.trim();
  const mode = getVocabMode();

  if (!userLanguageId) {
    showFeedback(elements.storyFeedback, "Choose a language first.", true);
    return;
  }

  const pool = getVocabularyPool(userLanguageId, prof);
  if (!pool.length) {
    showFeedback(elements.storyFeedback, "No vocabulary available for that filter.", true);
    return;
  }

  let vocabulary = [];
  if (mode === "manual") {
    const checkedIds = getCheckedVocabIds();
    vocabulary = pool.filter((item) => checkedIds.has(item.vocabId));
    if (!vocabulary.length) {
      showFeedback(elements.storyFeedback, "Select at least one word.", true);
      return;
    }
    vocabulary = sampleWords(vocabulary, maxWords);
  } else if (mode === "ai") {
    vocabulary = chooseVocabularyByTheme(pool, theme, maxWords);
  } else {
    vocabulary = sampleWords(pool, maxWords);
  }

  const lang = getUserLanguages(state.currentUserId).find(
    (entry) => entry.userLanguageId === userLanguageId
  );
  const user = currentUser();
  const story = buildStory(lang ? lang.name : "your language", vocabulary, user.name, theme);

  state.story = story;
  saveState();
  elements.storyOutput.textContent = story;
  showFeedback(
    elements.storyFeedback,
    `Story generated using ${vocabulary.length} words (${mode}).`
  );
}

function handleSaveStory() {
  const story = elements.storyOutput.textContent.trim();
  if (!story || story.startsWith("No story yet")) {
    showFeedback(elements.storyFeedback, "Generate a story first.", true);
    return;
  }

  const blob = new Blob([story], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "language-tutor-story.txt";
  anchor.click();
  URL.revokeObjectURL(url);
  showFeedback(elements.storyFeedback, "Story saved.");
}

function init() {
  updateAuthUI();
  setActiveView("view-account");

  elements.navButtons.forEach((btn) => {
    btn.addEventListener("click", handleNavClick);
  });

  elements.accountForm.addEventListener("submit", handleCreateAccount);
  elements.loginForm.addEventListener("submit", handleLogin);
  elements.logoutBtn.addEventListener("click", handleLogout);
  elements.enrollBtn.addEventListener("click", handleEnrollLanguage);
  elements.vocabForm.addEventListener("submit", handleAddVocab);
  elements.vocabLanguage.addEventListener("change", refreshVocabView);
  elements.storyLanguage.addEventListener("change", refreshStoryVocabList);
  elements.storyProf.addEventListener("change", refreshStoryVocabList);
  elements.vocabModeRadios.forEach((radio) => {
    radio.addEventListener("change", updateVocabPickerState);
  });
  elements.selectAll.addEventListener("click", handleSelectAll);
  elements.clearAll.addEventListener("click", handleClearAll);
  elements.storyForm.addEventListener("submit", handleGenerateStory);
  elements.saveStory.addEventListener("click", handleSaveStory);

  refreshLanguageViews();
  refreshVocabView();
  refreshStoryView();

  if (state.story) {
    elements.storyOutput.textContent = state.story;
  }
}

init();
