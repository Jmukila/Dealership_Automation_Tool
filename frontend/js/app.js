const API_BASE = `${window.location.origin}/api`;

const accountSelect = document.getElementById("accountSelect");
const dealershipList = document.getElementById("dealershipList");
const includeLogo = document.getElementById("includeLogo");
const logoUploadField = document.getElementById("logoUploadField");
const logoUpload = document.getElementById("logoUpload");
const backgroundUpload = document.getElementById("backgroundUpload");
const backgroundDropzone = document.getElementById("backgroundDropzone");
const backgroundFileName = document.getElementById("backgroundFileName");
const generatorForm = document.getElementById("generatorForm");
const formStatus = document.getElementById("formStatus");
const resultsList = document.getElementById("resultsList");
const zipDownload = document.getElementById("zipDownload");
const previewCanvas = document.getElementById("previewCanvas");
const progressWrap = document.getElementById("progressWrap");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");

let dealerships = [];
let backgroundImage = null;
let logoImage = null;
let progressTimer = null;

init();

async function init() {
  try {
    await loadAccounts();
    accountSelect.addEventListener("change", () => loadDealerships(accountSelect.value));
    includeLogo.addEventListener("change", handleLogoToggle);
    logoUpload.addEventListener("change", handleLogoUpload);
    backgroundUpload.addEventListener("change", handleBackgroundUpload);
    backgroundDropzone.addEventListener("dragover", handleDragOver);
    backgroundDropzone.addEventListener("dragleave", handleDragLeave);
    backgroundDropzone.addEventListener("drop", handleDrop);
    generatorForm.addEventListener("submit", submitGeneration);
    drawPreview();
  } catch (error) {
    formStatus.textContent = "Unable to load the app. Make sure the backend is running.";
  }
}

async function loadAccounts() {
  const response = await fetch(`${API_BASE}/accounts`);
  const accounts = await response.json();

  accountSelect.innerHTML = accounts
    .map((account) => `<option value="${account.id}">${account.name}</option>`)
    .join("");

  if (accounts.length > 0) {
    await loadDealerships(accounts[0].id);
  }
}

async function loadDealerships(accountId) {
  const response = await fetch(`${API_BASE}/dealerships?account_id=${accountId}`);
  dealerships = await response.json();

  dealershipList.innerHTML = dealerships
    .map(
      (dealer, index) => `
        <label class="dealer-option">
          <input type="checkbox" name="dealership_ids" value="${dealer.id}" ${index === 0 ? "checked" : ""}>
          <span>${dealer.name}</span>
        </label>
      `
    )
    .join("");

  dealershipList.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", drawPreview);
  });
  drawPreview();
}

function handleLogoToggle() {
  logoUploadField.classList.toggle("hidden", !includeLogo.checked);
  drawPreview();
}

async function handleLogoUpload() {
  const file = logoUpload.files[0];
  logoImage = file ? await loadImageFromFile(file) : null;
  drawPreview();
}

async function handleBackgroundUpload() {
  const file = backgroundUpload.files[0];
  backgroundFileName.textContent = file ? file.name : "No file selected";
  backgroundImage = file ? await loadImageFromFile(file) : null;
  drawPreview();
}

function handleDragOver(event) {
  event.preventDefault();
  backgroundDropzone.classList.add("is-dragging");
}

function handleDragLeave() {
  backgroundDropzone.classList.remove("is-dragging");
}

async function handleDrop(event) {
  event.preventDefault();
  backgroundDropzone.classList.remove("is-dragging");

  const file = Array.from(event.dataTransfer.files).find((item) =>
    ["image/jpeg", "image/png"].includes(item.type)
  );
  if (!file) {
    formStatus.textContent = "Please drop a JPG or PNG image.";
    return;
  }

  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  backgroundUpload.files = dataTransfer.files;
  await handleBackgroundUpload();
}

async function submitGeneration(event) {
  event.preventDefault();
  formStatus.textContent = "";
  resultsList.innerHTML = "";
  zipDownload.classList.add("hidden");

  const selectedDealerIds = getSelectedDealerIds();
  const selectedFormats = getSelectedFormats();

  if (!selectedDealerIds.length) {
    formStatus.textContent = "Select at least one dealership.";
    return;
  }
  if (!selectedFormats.length) {
    formStatus.textContent = "Select at least one output format.";
    return;
  }
  if (!backgroundUpload.files[0]) {
    formStatus.textContent = "Upload a background image first.";
    return;
  }

  const expectedCount = selectedDealerIds.length * selectedFormats.length;
  startProgress(expectedCount);

  const formData = new FormData();
  formData.append("account_id", accountSelect.value);
  selectedDealerIds.forEach((id) => formData.append("dealership_ids", id));
  selectedFormats.forEach((format) => formData.append("formats", format));
  formData.append("include_logo", includeLogo.checked ? "true" : "false");
  formData.append("background", backgroundUpload.files[0]);

  if (logoUpload.files[0]) {
    formData.append("uploaded_logo", logoUpload.files[0]);
  }

  try {
    const response = await fetch(`${API_BASE}/generate`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Generation failed.");
    }

    finishProgress(data.creatives.length);
    zipDownload.href = `${window.location.origin}${data.download_zip}`;
    zipDownload.classList.remove("hidden");

    resultsList.innerHTML = data.creatives
      .map(
        (creative) => `
          <article class="result-card">
            <img src="${window.location.origin}${creative.preview_url}" alt="${creative.dealership} ${labelFormat(creative.format)}">
            <div>
              <strong>${creative.dealership}</strong>
              <span>${labelFormat(creative.format)}</span>
            </div>
            <a href="${window.location.origin}${creative.download_url}" target="_blank" rel="noopener">Download</a>
          </article>
        `
      )
      .join("");
  } catch (error) {
    stopProgress();
    formStatus.textContent = error.message;
  }
}

function drawPreview() {
  const ctx = previewCanvas.getContext("2d");
  const width = previewCanvas.width;
  const height = previewCanvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#eef1f3";
  ctx.fillRect(0, 0, width, height);

  if (backgroundImage) {
    drawCoverImage(ctx, backgroundImage, width, height, 0.46);
  } else {
    ctx.fillStyle = "#68727c";
    ctx.font = "600 15px Manrope, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Upload a background to preview", width / 2, height / 2);
  }

  const dealer = getFirstSelectedDealer();
  if (dealer) {
    const panelUrl = `${API_BASE}/asset-file/${dealer.panel_path}`;
    drawRemotePanel(ctx, panelUrl, width, height);
  }

  if (includeLogo.checked && logoImage) {
    const maxLogoWidth = width * 0.16;
    const scale = Math.min(maxLogoWidth / logoImage.width, 1);
    const logoWidth = logoImage.width * scale;
    const logoHeight = logoImage.height * scale;
    ctx.drawImage(logoImage, width - logoWidth - 18, 18, logoWidth, logoHeight);
  }
}

function drawRemotePanel(ctx, url, width, height) {
  const panel = new Image();
  panel.onload = () => {
    const scale = width / panel.width;
    const panelHeight = panel.height * scale;
    ctx.drawImage(panel, 0, height - panelHeight, width, panelHeight);
  };
  panel.src = url;
}

function drawCoverImage(ctx, image, width, height, focusY) {
  const sourceRatio = image.width / image.height;
  const targetRatio = width / height;
  const scale = sourceRatio > targetRatio ? height / image.height : width / image.width;
  const resizedWidth = image.width * scale;
  const resizedHeight = image.height * scale;
  const left = (width - resizedWidth) / 2;
  const top = Math.min(Math.max(height * 0.5 - resizedHeight * focusY, height - resizedHeight), 0);
  ctx.drawImage(image, left, top, resizedWidth, resizedHeight);
}

function getSelectedDealerIds() {
  return Array.from(dealershipList.querySelectorAll("input:checked")).map((input) => input.value);
}

function getSelectedFormats() {
  return Array.from(document.querySelectorAll('input[name="formats"]:checked')).map((checkbox) => checkbox.value);
}

function getFirstSelectedDealer() {
  const selectedId = getSelectedDealerIds()[0];
  return dealerships.find((dealer) => String(dealer.id) === selectedId);
}

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = URL.createObjectURL(file);
  });
}

function startProgress(expectedCount) {
  let progress = 8;
  progressWrap.classList.remove("hidden");
  progressBar.style.width = `${progress}%`;
  progressText.textContent = `Generating ${expectedCount} creatives...`;

  clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    progress = Math.min(progress + 7, 92);
    progressBar.style.width = `${progress}%`;
  }, 220);
}

function finishProgress(count) {
  clearInterval(progressTimer);
  progressBar.style.width = "100%";
  progressText.textContent = `Created ${count} creatives.`;
  formStatus.textContent = "Generation completed successfully.";
}

function stopProgress() {
  clearInterval(progressTimer);
  progressWrap.classList.add("hidden");
  progressBar.style.width = "0%";
}

function labelFormat(format) {
  const labels = {
    "post-square": "1080x1080",
    "post-portrait": "1080x1350",
    story: "1080x1920",
  };
  return labels[format] || format;
}
