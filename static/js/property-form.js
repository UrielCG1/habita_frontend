document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("id_images");
  const dropzone = document.querySelector(".upload-dropzone--rich");
  const galleryGrid = document.getElementById("gallery-grid");
  const galleryOrderInput = document.getElementById("gallery-order-input");
  const coverTokenInput = document.getElementById("cover-token-input");
  const emptyState = document.getElementById("gallery-empty-state");
  const form = document.getElementById("property-form");
  const deleteForm = document.getElementById("property-image-delete-form");

  if (!galleryGrid || !galleryOrderInput || !coverTokenInput || !form) return;

  let newItems = [];
  let newCounter = 0;
  let draggedToken = null;

  const allCards = () => Array.from(galleryGrid.querySelectorAll(".gallery-card"));

  const existingCards = () =>
    Array.from(galleryGrid.querySelectorAll('.gallery-card[data-kind="existing"]'));

  if (!coverTokenInput.value) {
    const activeCover = existingCards().find((card) => card.classList.contains("is-cover"));
    if (activeCover) {
      coverTokenInput.value = activeCover.dataset.token || "";
    }
  }

  const updateEmptyState = () => {
    if (!emptyState) return;
    emptyState.classList.toggle("is-hidden", galleryGrid.children.length > 0);
  };

  const syncGalleryOrder = () => {
    const tokens = allCards()
      .map((card) => card.dataset.token)
      .filter(Boolean);

    galleryOrderInput.value = tokens.join(",");
  };

  const syncCoverVisualState = () => {
    const coverToken = coverTokenInput.value;

    allCards().forEach((card) => {
      const isCover = card.dataset.token === coverToken;
      const button = card.querySelector(".js-set-cover");

      card.classList.toggle("is-cover", isCover);

      if (button) {
        const label = button.querySelector("span:last-child");
        if (label) {
          label.textContent = isCover ? "Principal" : "Hacer principal";
        }
      }

      const footerSmall = card.querySelector(".gallery-card__footer small");
      if (footerSmall) {
        if (card.dataset.kind === "existing") {
          footerSmall.textContent = isCover ? "Actualmente principal" : "Imagen existente";
        } else {
          footerSmall.textContent = isCover ? "Nueva imagen principal" : "Nueva imagen";
        }
      }
    });
  };

  const syncFileInput = () => {
    if (!input) return;

    const dataTransfer = new DataTransfer();
    newItems.forEach((item) => dataTransfer.items.add(item.file));
    input.files = dataTransfer.files;
  };

  const revokeNewUrls = () => {
    newItems.forEach((item) => {
      if (item.previewUrl) {
        URL.revokeObjectURL(item.previewUrl);
      }
    });
  };

  const createNewCard = (item) => {
    const card = document.createElement("article");
    card.className = "gallery-card";
    card.draggable = true;
    card.dataset.token = item.token;
    card.dataset.kind = "new";

    card.innerHTML = `
      <div class="gallery-card__media">
        <img src="${item.previewUrl}" alt="${item.file.name}">
        <button type="button" class="gallery-chip gallery-chip--drag" title="Ordenar">
          <span class="material-symbols-outlined">drag_indicator</span>
        </button>
        <button type="button" class="gallery-chip gallery-chip--cover js-set-cover" data-token="${item.token}">
          <span class="material-symbols-outlined">star</span>
          <span>Hacer principal</span>
        </button>
        <div class="gallery-card__overlay">
          <button type="button" class="gallery-icon-btn gallery-icon-btn--danger js-remove-new-image" data-token="${item.token}" title="Eliminar imagen">
            <span class="material-symbols-outlined">delete</span>
          </button>
        </div>
      </div>
      <div class="gallery-card__footer">
        <strong>${item.file.name}</strong>
        <small>Nueva imagen</small>
      </div>
    `;

    return card;
  };

  const renderNewItems = () => {
    Array.from(
      galleryGrid.querySelectorAll('.gallery-card[data-kind="new"]')
    ).forEach((card) => card.remove());

    const orderedTokens = (galleryOrderInput.value || "")
      .split(",")
      .map((token) => token.trim())
      .filter(Boolean);

    const normalizedTokens = orderedTokens.filter((token) => token.startsWith("e:"));
    newItems.forEach((item) => normalizedTokens.push(item.token));

    normalizedTokens.forEach((token) => {
      const newItem = newItems.find((item) => item.token === token);
      if (newItem) {
        galleryGrid.appendChild(createNewCard(newItem));
      }
    });

    syncFileInput();
    syncGalleryOrder();
    syncCoverVisualState();
    updateEmptyState();
    bindGalleryCardEvents();
  };

  const moveTokenToFront = (token) => {
    const current = (galleryOrderInput.value || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    const next = [token, ...current.filter((item) => item !== token)];
    galleryOrderInput.value = next.join(",");

    const card = allCards().find((node) => node.dataset.token === token);
    if (card) {
      galleryGrid.prepend(card);
    }
  };

  const setCoverToken = (token) => {
    coverTokenInput.value = token;
    moveTokenToFront(token);

    if (token.startsWith("n:")) {
      const index = newItems.findIndex((item) => item.token === token);
      if (index > 0) {
        const [selected] = newItems.splice(index, 1);
        newItems.unshift(selected);
        syncFileInput();
      }
    }

    syncGalleryOrder();
    syncCoverVisualState();
  };

  const removeNewItem = (token) => {
    const index = newItems.findIndex((item) => item.token === token);
    if (index === -1) return;

    const [removed] = newItems.splice(index, 1);
    if (removed?.previewUrl) {
      URL.revokeObjectURL(removed.previewUrl);
    }

    if (coverTokenInput.value === token) {
      const firstExisting = existingCards()[0];
      const firstNew = newItems[0];
      coverTokenInput.value = firstExisting?.dataset.token || firstNew?.token || "";
    }

    renderNewItems();
  };

  const submitDeleteExistingImage = (url) => {
    if (!deleteForm || !url) return;

    deleteForm.action = url;
    deleteForm.submit();
  };

  const handleFiles = (files) => {
    const imageFiles = Array.from(files || []).filter((file) =>
      file.type.startsWith("image/")
    );

    if (!imageFiles.length) return;

    imageFiles.forEach((file) => {
      const token = `n:${newCounter++}`;
      newItems.push({
        token,
        file,
        previewUrl: URL.createObjectURL(file),
      });
    });

    if (!coverTokenInput.value || !allCards().length) {
      coverTokenInput.value = newItems[0]?.token || coverTokenInput.value;
    }

    renderNewItems();
  };

  const bindGalleryCardEvents = () => {
    allCards().forEach((card) => {
      card.ondragstart = () => {
        draggedToken = card.dataset.token;
        card.classList.add("is-dragging");
      };

      card.ondragend = () => {
        draggedToken = null;
        card.classList.remove("is-dragging");
      };

      card.ondragover = (event) => {
        event.preventDefault();
      };

      card.ondrop = (event) => {
        event.preventDefault();

        const targetToken = card.dataset.token;
        if (!draggedToken || !targetToken || draggedToken === targetToken) return;

        const cards = allCards();
        const draggedCard = cards.find((node) => node.dataset.token === draggedToken);
        const targetCard = cards.find((node) => node.dataset.token === targetToken);

        if (!draggedCard || !targetCard) return;

        const draggedIndex = cards.indexOf(draggedCard);
        const targetIndex = cards.indexOf(targetCard);

        if (draggedIndex < targetIndex) {
          targetCard.after(draggedCard);
        } else {
          targetCard.before(draggedCard);
        }

        const orderedTokens = allCards().map((node) => node.dataset.token);
        galleryOrderInput.value = orderedTokens.join(",");

        const newOrder = orderedTokens.filter((token) => token.startsWith("n:"));
        newItems.sort((a, b) => newOrder.indexOf(a.token) - newOrder.indexOf(b.token));

        syncFileInput();
        syncCoverVisualState();
        updateEmptyState();
      };
    });

    galleryGrid.querySelectorAll(".js-set-cover").forEach((button) => {
      button.onclick = (event) => {
        event.preventDefault();
        const token = button.dataset.token;
        if (!token) return;
        setCoverToken(token);
      };
    });

    galleryGrid.querySelectorAll(".js-remove-new-image").forEach((button) => {
      button.onclick = (event) => {
        event.preventDefault();
        const token = button.dataset.token;
        if (!token) return;
        removeNewItem(token);
      };
    });

    galleryGrid.querySelectorAll(".js-delete-existing-image").forEach((button) => {
      button.onclick = (event) => {
        event.preventDefault();
        const url = button.dataset.deleteUrl;
        if (!url) return;

        const ok = window.confirm("¿Deseas eliminar esta imagen?");
        if (!ok) return;

        submitDeleteExistingImage(url);
      };
    });
  };

  if (input) {
    input.addEventListener("change", () => {
      handleFiles(input.files);
      input.value = "";
    });
  }

  if (dropzone && input) {
    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.add("is-dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.remove("is-dragover");
      });
    });

    dropzone.addEventListener("drop", (event) => {
      handleFiles(event.dataTransfer?.files || []);
    });
  }

  form.addEventListener("submit", () => {
    syncGalleryOrder();
    syncFileInput();
  });

  syncGalleryOrder();
  syncCoverVisualState();
  updateEmptyState();
  bindGalleryCardEvents();

  window.addEventListener("beforeunload", revokeNewUrls);

  const previewButton = document.getElementById("preview-location-btn");
  const previewStatus = document.getElementById("property-location-preview-status");
  const previewMapNode = document.getElementById("property-location-preview-map");

  let previewMap = null;
  let previewMarker = null;

  function readStructuredLocationFields() {
    return {
      street: document.getElementById("id_address_line")?.value?.trim() || "",
      county: document.getElementById("id_neighborhood")?.value?.trim() || "",
      city: document.getElementById("id_city")?.value?.trim() || "",
      state: document.getElementById("id_state")?.value?.trim() || "",
      postalcode: document.getElementById("id_postal_code")?.value?.trim() || "",
      country: "Mexico",
    };
  }

  function buildStructuredLocationParams(fields) {
    const params = new URLSearchParams();

    if (fields.street) params.append("street", fields.street);
    if (fields.county) params.append("county", fields.county);
    if (fields.city) params.append("city", fields.city);
    if (fields.state) params.append("state", fields.state);
    if (fields.postalcode) params.append("postalcode", fields.postalcode);
    if (fields.country) params.append("country", fields.country);

    return params;
  }

  function ensurePreviewMap(lat, lng, title) {
    if (!previewMapNode || typeof L === "undefined") return;

    if (!previewMap) {
      previewMap = L.map(previewMapNode).setView([lat, lng], 15);

      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
      }).addTo(previewMap);
    } else {
      previewMap.setView([lat, lng], 15);
    }

    if (previewMarker) {
      previewMarker.remove();
    }

    previewMarker = L.marker([lat, lng]).addTo(previewMap);

    if (title) {
      previewMarker.bindPopup(title).openPopup();
    }

    setTimeout(() => {
      previewMap.invalidateSize();
    }, 120);
  }

  async function fetchLocationPreview() {
    if (!previewButton || !previewStatus) return;

    const fields = readStructuredLocationFields();

    if (!fields.city || !fields.state) {
      previewStatus.textContent = "Captura al menos ciudad y estado.";
      return;
    }

    if (!fields.street && !fields.county && !fields.postalcode) {
      previewStatus.textContent = "Captura al menos calle, colonia o código postal.";
      return;
    }

    const previewUrl = previewButton.dataset.previewUrl;
    if (!previewUrl) return;

    previewStatus.textContent = "Buscando ubicación aproximada...";

    const params = buildStructuredLocationParams(fields);

    try {
      const response = await fetch(`${previewUrl}?${params.toString()}`, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      const payload = await response.json();

      if (!response.ok || !payload.success) {
        previewStatus.textContent = payload.error || "No se pudo calcular la ubicación.";
        return;
      }

      const data = payload.data;

      document.getElementById("id_latitude").value = data.latitude;
      document.getElementById("id_longitude").value = data.longitude;

      previewStatus.textContent = data.display_name || "Ubicación aproximada encontrada.";
      ensurePreviewMap(data.latitude, data.longitude, data.display_name || "Ubicación aproximada");
    } catch (error) {
      previewStatus.textContent = "No fue posible consultar la ubicación aproximada.";
    }
  }

  if (previewButton) {
    previewButton.addEventListener("click", fetchLocationPreview);
  }
});