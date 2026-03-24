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

  const updateEmptyState = () => {
    if (!emptyState) return;
    emptyState.classList.toggle("is-hidden", allCards().length > 0);
  };

  const syncGalleryOrder = () => {
    const tokens = allCards()
      .map((card) => card.dataset.token)
      .filter(Boolean);

    galleryOrderInput.value = tokens.join(",");
  };

  const syncNewItemsOrderFromDom = () => {
    const orderedNewTokens = allCards()
      .map((card) => card.dataset.token)
      .filter((token) => token && token.startsWith("n:"));

    newItems.sort((a, b) => {
      return orderedNewTokens.indexOf(a.token) - orderedNewTokens.indexOf(b.token);
    });
  };

  const syncFileInput = () => {
    if (!input) return;

    const dataTransfer = new DataTransfer();
    newItems.forEach((item) => dataTransfer.items.add(item.file));
    input.files = dataTransfer.files;
  };

  const syncCoverVisualState = () => {
    const coverToken = (coverTokenInput.value || "").trim();

    allCards().forEach((card) => {
      const isCover = card.dataset.token === coverToken;
      const button = card.querySelector(".js-set-cover");
      const label = button?.querySelector(".gallery-chip__label");
      const footerSmall = card.querySelector(".gallery-card__footer small");

      card.classList.toggle("is-cover", isCover);

      if (label) {
        label.textContent = isCover ? "Principal" : "Hacer principal";
      }

      if (footerSmall) {
        if (card.dataset.kind === "existing") {
          footerSmall.textContent = isCover ? "Actualmente principal" : "Imagen existente";
        } else {
          footerSmall.textContent = isCover ? "Nueva imagen principal" : "Nueva imagen";
        }
      }
    });
  };

  const moveTokenToFront = (token) => {
    if (!token) return;

    const card = allCards().find((node) => node.dataset.token === token);
    if (!card) return;

    galleryGrid.prepend(card);
    syncGalleryOrder();
    syncNewItemsOrderFromDom();
    syncFileInput();
  };

  const setCoverToken = (token) => {
    if (!token) return;

    coverTokenInput.value = token;
    moveTokenToFront(token);
    syncCoverVisualState();
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
    card.draggable = false;
    card.dataset.token = item.token;
    card.dataset.kind = "new";

    card.innerHTML = `
      <div class="gallery-card__media">
        <img src="${item.previewUrl}" alt="${item.file.name}">
        <button type="button" class="gallery-chip gallery-chip--drag js-drag-handle" title="Ordenar">
          <span class="material-symbols-outlined">drag_indicator</span>
        </button>
        <button type="button" class="gallery-chip gallery-chip--cover js-set-cover" data-token="${item.token}">
          <span class="material-symbols-outlined">star</span>
          <span class="gallery-chip__label">Hacer principal</span>
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

  const renderGallery = () => {
    const existingMap = new Map();
    existingCards().forEach((card) => {
      existingMap.set(card.dataset.token, card);
    });

    const desiredTokens = (galleryOrderInput.value || "")
      .split(",")
      .map((token) => token.trim())
      .filter(Boolean);

    existingCards().forEach((card) => {
      if (!desiredTokens.includes(card.dataset.token)) {
        desiredTokens.push(card.dataset.token);
      }
    });

    newItems.forEach((item) => {
      if (!desiredTokens.includes(item.token)) {
        desiredTokens.push(item.token);
      }
    });

    galleryGrid.innerHTML = "";

    desiredTokens.forEach((token) => {
      if (existingMap.has(token)) {
        const existingCard = existingMap.get(token);
        existingCard.draggable = false;
        galleryGrid.appendChild(existingCard);
        return;
      }

      const newItem = newItems.find((item) => item.token === token);
      if (newItem) {
        galleryGrid.appendChild(createNewCard(newItem));
      }
    });

    syncGalleryOrder();
    syncNewItemsOrderFromDom();
    syncFileInput();
    syncCoverVisualState();
    updateEmptyState();
  };

  const removeNewItem = (token) => {
    const index = newItems.findIndex((item) => item.token === token);
    if (index === -1) return;

    const [removed] = newItems.splice(index, 1);
    if (removed?.previewUrl) {
      URL.revokeObjectURL(removed.previewUrl);
    }

    const orderedTokens = (galleryOrderInput.value || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
      .filter((item) => item !== token);

    galleryOrderInput.value = orderedTokens.join(",");

    if (coverTokenInput.value === token) {
      const firstRemaining = orderedTokens[0] || "";
      coverTokenInput.value = firstRemaining;
    }

    renderGallery();
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

      const currentTokens = (galleryOrderInput.value || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

      currentTokens.push(token);
      galleryOrderInput.value = currentTokens.join(",");
    });

    if (!coverTokenInput.value) {
      coverTokenInput.value = newItems[0]?.token || "";
    }

    renderGallery();
  };

  const disableDragging = () => {
    allCards().forEach((card) => {
      card.draggable = false;
      card.classList.remove("is-dragging-ready");
      card.classList.remove("is-dragging");
    });
  };

  const initializeFromServer = () => {
    allCards().forEach((card) => {
      card.draggable = false;
    });

    if (!galleryOrderInput.value) {
      syncGalleryOrder();
    }

    if (!coverTokenInput.value) {
      const coverCard = allCards().find((card) => card.classList.contains("is-cover"));
      if (coverCard) {
        coverTokenInput.value = coverCard.dataset.token || "";
      }
    }

    syncCoverVisualState();
    updateEmptyState();
  };

  galleryGrid.addEventListener("click", (event) => {
    const coverButton = event.target.closest(".js-set-cover");
    if (coverButton) {
      event.preventDefault();
      event.stopPropagation();
      setCoverToken(coverButton.dataset.token);
      return;
    }

    const removeNewButton = event.target.closest(".js-remove-new-image");
    if (removeNewButton) {
      event.preventDefault();
      event.stopPropagation();
      removeNewItem(removeNewButton.dataset.token);
      return;
    }

    const deleteExistingButton = event.target.closest(".js-delete-existing-image");
    if (deleteExistingButton) {
      event.preventDefault();
      event.stopPropagation();

      const url = deleteExistingButton.dataset.deleteUrl;
      if (!url) return;

      const ok = window.confirm("¿Deseas eliminar esta imagen?");
      if (!ok) return;

      submitDeleteExistingImage(url);
    }
  });

  galleryGrid.addEventListener("mousedown", (event) => {
    const handle = event.target.closest(".js-drag-handle");
    if (!handle) {
      disableDragging();
      return;
    }

    const card = handle.closest(".gallery-card");
    if (!card) return;

    disableDragging();
    card.draggable = true;
    card.classList.add("is-dragging-ready");
  });

  galleryGrid.addEventListener("dragstart", (event) => {
    const card = event.target.closest(".gallery-card");
    if (!card || !card.draggable) {
      event.preventDefault();
      return;
    }

    draggedToken = card.dataset.token || null;
    card.classList.remove("is-dragging-ready");
    card.classList.add("is-dragging");

    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", draggedToken || "");
    }
  });

  galleryGrid.addEventListener("dragover", (event) => {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "move";
    }
  });

  galleryGrid.addEventListener("drop", (event) => {
    event.preventDefault();

    const targetCard = event.target.closest(".gallery-card");
    if (!targetCard || !draggedToken) return;

    const draggedCard = allCards().find((card) => card.dataset.token === draggedToken);
    if (!draggedCard || draggedCard === targetCard) return;

    const rect = targetCard.getBoundingClientRect();
    const before = event.clientY < rect.top + rect.height / 2;

    if (before) {
      galleryGrid.insertBefore(draggedCard, targetCard);
    } else {
      galleryGrid.insertBefore(draggedCard, targetCard.nextSibling);
    }

    syncGalleryOrder();
    syncNewItemsOrderFromDom();
    syncFileInput();
    syncCoverVisualState();
  });

  galleryGrid.addEventListener("dragend", () => {
    draggedToken = null;
    disableDragging();
    syncGalleryOrder();
  });

  if (input) {
    input.addEventListener("change", () => {
      handleFiles(input.files);
      input.value = "";
    });
  }

  if (dropzone) {
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
    syncNewItemsOrderFromDom();
    syncFileInput();
  });

  initializeFromServer();
  window.addEventListener("beforeunload", revokeNewUrls);
});