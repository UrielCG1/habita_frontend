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

  const disableAllDragging = () => {
    allCards().forEach((card) => {
      card.draggable = false;
      card.classList.remove("is-draggable");
    });
  };

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
    const coverToken = (coverTokenInput.value || "").trim();

    allCards().forEach((card) => {
      const isCover = card.dataset.token === coverToken;
      const button = card.querySelector(".js-set-cover");

      card.classList.toggle("is-cover", isCover);

      if (button) {
        const textNode = button.querySelector(".gallery-chip__label");
        if (textNode) {
          textNode.textContent = isCover ? "Principal" : "Hacer principal";
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

    disableAllDragging();
    syncFileInput();
    syncGalleryOrder();
    syncCoverVisualState();
    updateEmptyState();
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
    if (!token) return;

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

  const initializeServerCards = () => {
    allCards().forEach((card) => {
      card.draggable = false;

      const coverButton = card.querySelector(".js-set-cover");
      if (coverButton) {
        const secondSpan = coverButton.querySelectorAll("span")[1];
        if (secondSpan && !secondSpan.classList.contains("gallery-chip__label")) {
          secondSpan.classList.add("gallery-chip__label");
        }
      }
    });

    if (!coverTokenInput.value) {
      const activeCover = existingCards().find((card) => card.classList.contains("is-cover"));
      if (activeCover) {
        coverTokenInput.value = activeCover.dataset.token || "";
      }
    }

    syncGalleryOrder();
    syncCoverVisualState();
    updateEmptyState();
  };

  galleryGrid.addEventListener("click", (event) => {
    const coverButton = event.target.closest(".js-set-cover");
    if (coverButton) {
      event.preventDefault();
      event.stopPropagation();
      const token = coverButton.dataset.token;
      setCoverToken(token);
      return;
    }

    const removeNewButton = event.target.closest(".js-remove-new-image");
    if (removeNewButton) {
      event.preventDefault();
      event.stopPropagation();
      const token = removeNewButton.dataset.token;
      removeNewItem(token);
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
    const dragHandle = event.target.closest(".js-drag-handle");
    if (!dragHandle) {
      disableAllDragging();
      return;
    }

    const card = dragHandle.closest(".gallery-card");
    if (!card) return;

    disableAllDragging();
    card.draggable = true;
    card.classList.add("is-draggable");
  });

  galleryGrid.addEventListener("dragstart", (event) => {
    const card = event.target.closest(".gallery-card");
    if (!card || !card.draggable) {
      event.preventDefault();
      return;
    }

    draggedToken = card.dataset.token || null;
    card.classList.add("is-dragging");
  });

  galleryGrid.addEventListener("dragend", (event) => {
    const card = event.target.closest(".gallery-card");
    if (card) {
      card.classList.remove("is-dragging");
    }
    draggedToken = null;
    disableAllDragging();
  });

  galleryGrid.addEventListener("dragover", (event) => {
    event.preventDefault();
  });

  galleryGrid.addEventListener("drop", (event) => {
    event.preventDefault();

    const targetCard = event.target.closest(".gallery-card");
    if (!targetCard || !draggedToken) return;

    const draggedCard = allCards().find((node) => node.dataset.token === draggedToken);
    if (!draggedCard || draggedCard === targetCard) return;

    const cards = allCards();
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
  });

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

  initializeServerCards();
  window.addEventListener("beforeunload", revokeNewUrls);
});