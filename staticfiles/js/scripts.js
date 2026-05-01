/* JS centralizado desde templates */

/* ===== add_stock.html :: script 1 ===== */
(function () {
        const form = document.getElementById('stock-wizard-form');
        if (!form) {
            return;
        }

        const steps = Array.from(form.querySelectorAll('.wizard-step'));
        const progress = Array.from(document.querySelectorAll('.wizard-progress-step'));
        const prevBtn = document.getElementById('wizard-prev');
        const nextBtn = document.getElementById('wizard-next');
        const submitBtn = document.getElementById('wizard-submit');
        const summary = document.getElementById('wizard-summary');
        const descriptionField = form.querySelector('textarea[name="Descrepción"]') || form.querySelector('textarea');
        const lookupBtn = document.getElementById('vehicle-lookup-btn');
        const lookupStatus = document.getElementById('vehicle-lookup-status');
        const lookupUrl = form.dataset.lookupUrl;

        let currentStep = 0;

        function getField(name) {
            return form.querySelector('[name="' + name + '"]');
        }

        function setLookupStatus(message, isError) {
            if (!lookupStatus) {
                return;
            }
            lookupStatus.textContent = message || '';
            lookupStatus.style.color = isError ? '#b91c1c' : '#374151';
        }

        function setFieldValue(field, value) {
            if (!field || value === undefined || value === null) {
                return;
            }

            const normalized = String(value).trim();
            if (!normalized) {
                return;
            }

            if (field.tagName === 'SELECT') {
                const options = Array.from(field.options);
                const target = normalized.toLowerCase();
                const match = options.find(function (option) {
                    return option.value.toLowerCase() === target || option.text.toLowerCase() === target;
                });
                if (match) {
                    field.value = match.value;
                }
            } else {
                field.value = normalized;
            }

            field.dispatchEvent(new Event('input', { bubbles: true }));
            field.dispatchEvent(new Event('change', { bubbles: true }));
        }

        async function autoFillVehicleData() {
            if (!lookupUrl) {
                setLookupStatus('Ruta de búsqueda no disponible.', true);
                return;
            }

            const matricula = (getField('Matricula')?.value || '').trim();
            const vin = (getField('VIN')?.value || '').trim();

            if (!matricula && !vin) {
                setLookupStatus('Introduce matrícula o VIN para autocompletar.', true);
                return;
            }

            lookupBtn.disabled = true;
            setLookupStatus('Consultando datos del vehículo...', false);

            try {
                const params = new URLSearchParams();
                if (matricula) params.set('matricula', matricula);
                if (vin) params.set('vin', vin);

                const response = await fetch(lookupUrl + '?' + params.toString(), {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                const payload = await response.json();

                if (!response.ok || !payload.ok) {
                    throw new Error(payload.error || 'No se pudieron obtener datos.');
                }

                const data = payload.data || {};
                setFieldValue(getField('Titulo'), data.Titulo);
                setFieldValue(getField('Marca'), data.Marca);
                setFieldValue(getField('Modelo'), data.Modelo);
                setFieldValue(getField('Año'), data.Año);
                setFieldValue(getField('Kilometros'), data.Kilometros);
                setFieldValue(getField('Versión'), data.Versión);
                setFieldValue(getField('Carrocería'), data.Carrocería);
                setFieldValue(getField('Puertas'), data.Puertas);
                setFieldValue(getField('Motor'), data.Motor);
                setFieldValue(getField('Tracción'), data.Tracción);
                setFieldValue(getField('Transmisión'), data.Transmisión);
                setFieldValue(getField('Combustible'), data.Combustible);
                setFieldValue(getField('Fecha_matriculación'), data.Fecha_matriculación);
                setFieldValue(getField('color'), data.color);
                setFieldValue(getField('Matricula'), data.Matricula || matricula);
                setFieldValue(getField('VIN'), data.VIN || vin);

                setLookupStatus('Datos autocompletados correctamente.', false);
            } catch (error) {
                setLookupStatus(error.message || 'Error consultando la API de vehículos.', true);
            } finally {
                lookupBtn.disabled = false;
            }
        }

        function syncEditor() {
            if (!descriptionField) {
                return;
            }

            if (window.editors && window.editors[descriptionField.id]) {
                descriptionField.value = window.editors[descriptionField.id].getData();
            }
        }

        function getFieldsForStep(stepElement) {
            return Array.from(stepElement.querySelectorAll('input, textarea, select')).filter(function (field) {
                return field.type !== 'hidden' && !field.disabled;
            });
        }

        function validateStep(stepIndex) {
            syncEditor();
            const fields = getFieldsForStep(steps[stepIndex]);
            for (const field of fields) {
                if (field.type === 'file') {
                    continue;
                }
                if (!field.checkValidity()) {
                    field.reportValidity();
                    field.focus();
                    return false;
                }
            }
            return true;
        }

        function formatFieldValue(field) {
            if (field.type === 'file') {
                return field.files && field.files.length ? field.files[0].name : 'Sin archivo';
            }
            if (field.tagName === 'SELECT') {
                return field.options[field.selectedIndex] ? field.options[field.selectedIndex].text : '';
            }
            return field.value ? field.value : 'Sin completar';
        }

        function buildSummary() {
            if (!summary) {
                return;
            }
            syncEditor();
            const fields = Array.from(form.querySelectorAll('.wizard-field'));
            summary.innerHTML = '';

            fields.forEach(function (wrapper) {
                const label = wrapper.getAttribute('data-summary-label') || 'Campo';
                const field = wrapper.querySelector('input, textarea, select');
                if (!field) {
                    return;
                }

                const row = document.createElement('div');
                row.className = 'wizard-summary-row';
                row.innerHTML = '<div class="wizard-summary-label"></div><div class="wizard-summary-value"></div>';
                row.querySelector('.wizard-summary-label').textContent = label;
                row.querySelector('.wizard-summary-value').textContent = formatFieldValue(field);
                summary.appendChild(row);
            });
        }

        function renderStep() {
            steps.forEach(function (step, index) {
                step.classList.toggle('active', index === currentStep);
            });

            progress.forEach(function (item, index) {
                item.classList.toggle('active', index <= currentStep);
            });

            prevBtn.disabled = currentStep === 0;
            const isLast = currentStep === steps.length - 1;
            nextBtn.style.display = isLast ? 'none' : 'inline-block';
            submitBtn.style.display = isLast ? 'inline-block' : 'none';

            if (isLast) {
                buildSummary();
            }
        }

        nextBtn.addEventListener('click', function () {
            if (!validateStep(currentStep)) {
                return;
            }
            if (currentStep < steps.length - 1) {
                currentStep += 1;
                renderStep();
            }
        });

        prevBtn.addEventListener('click', function () {
            if (currentStep > 0) {
                currentStep -= 1;
                renderStep();
            }
        });

        form.addEventListener('submit', function (event) {
            syncEditor();
            if (!validateStep(steps.length - 2)) {
                event.preventDefault();
            }
        });

        if (lookupBtn) {
            lookupBtn.addEventListener('click', autoFillVehicleData);
        }

        renderStep();
    })();
/* ===== end add_stock.html :: script 1 ===== */

/* ===== base.html :: script 1 ===== */
(function () {
            const ldSource = document.getElementById('seo-json-ld-data');
            if (!ldSource) {
                return;
            }
            const ldScript = document.createElement('script');
            ldScript.type = 'application/ld+json';
            ldScript.text = ldSource.textContent;
            document.head.appendChild(ldScript);
        })();
/* ===== end base.html :: script 1 ===== */

/* ===== base.html :: script 2 ===== */
(function () {
            const toggleButton = document.querySelector('.nav-toggle');
            const navMenu = document.getElementById('nav-menu');
            if (!toggleButton || !navMenu) {
                return;
            }

            function openMenu() {
                navMenu.classList.add('open');
                toggleButton.setAttribute('aria-expanded', 'true');
                document.body.classList.add('nav-open');
            }

            function closeMenu() {
                navMenu.classList.remove('open');
                toggleButton.setAttribute('aria-expanded', 'false');
                document.body.classList.remove('nav-open');
            }

            toggleButton.addEventListener('click', function () {
                if (navMenu.classList.contains('open')) {
                    closeMenu();
                } else {
                    openMenu();
                }
            });

            navMenu.querySelectorAll('a').forEach(function (link) {
                link.addEventListener('click', function () {
                    closeMenu();
                });
            });

            document.addEventListener('click', function (event) {
                const clickedInsideMenu = navMenu.contains(event.target);
                const clickedToggle = toggleButton.contains(event.target);
                if (!clickedInsideMenu && !clickedToggle) {
                    closeMenu();
                }
            });

            document.addEventListener('keydown', function (event) {
                if (event.key === 'Escape' && navMenu.classList.contains('open')) {
                    closeMenu();
                    toggleButton.focus();
                }
            });
        })();

        (function () {
            const flashItems = Array.from(document.querySelectorAll('[data-flash]'));
            if (!flashItems.length) {
                return;
            }

            function hideFlash(node) {
                if (!node || node.classList.contains('hiding')) {
                    return;
                }
                node.classList.add('hiding');
                window.setTimeout(function () {
                    node.remove();
                }, 220);
            }

            flashItems.forEach(function (item) {
                const closeButton = item.querySelector('[data-flash-close]');
                if (closeButton) {
                    closeButton.addEventListener('click', function () {
                        hideFlash(item);
                    });
                }

                window.setTimeout(function () {
                    hideFlash(item);
                }, 3000);
            });
        })();
/* ===== end base.html :: script 2 ===== */

/* ===== contact_messages_admin.html :: script 1 ===== */
(function () {
    async function openMessage(id, name, email, phone, subject, message, isUnread) {
        document.getElementById('modalSubject').textContent = subject;
        document.getElementById('modalFrom').textContent = 'De: ' + name;
        document.getElementById('modalEmail').textContent = email;
        document.getElementById('modalPhone').textContent = phone || 'No proporcionado';
        document.getElementById('modalMessage').textContent = message;
        document.getElementById('messageModal').classList.add('show');

        if (isUnread) {
            await markMessageAsRead(id);
            updateMessageAsReadUI(id);
        }
    }

    async function markMessageAsRead(id) {
        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            return;
        }

        const body = new URLSearchParams();
        body.append('mark_read_message', String(id));
        body.append('csrfmiddlewaretoken', csrfToken);

        try {
            await fetch(window.location.pathname, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                },
                body: body.toString(),
            });
        } catch (error) {
            console.error('No se pudo marcar el mensaje como leído:', error);
        }
    }

    function updateMessageAsReadUI(id) {
        const row = document.getElementById('message-row-' + id);
        if (row) {
            row.classList.remove('unread');
        }

        const badge = document.getElementById('message-unread-badge-' + id);
        if (badge) {
            badge.remove();
            updateUnreadCounters();
        }
    }

    function updateUnreadCounters() {
        const adminUnreadBadge = document.getElementById('admin-unread-badge');
        if (adminUnreadBadge) {
            const currentText = adminUnreadBadge.textContent || '';
            const currentCount = parseInt(currentText.replace(/\D+/g, ''), 10);

            if (!Number.isNaN(currentCount)) {
                const nextCount = Math.max(0, currentCount - 1);
                if (nextCount > 0) {
                    adminUnreadBadge.textContent = 'Nuevos: ' + nextCount;
                } else {
                    adminUnreadBadge.remove();
                }
            }
        }

        const navBadge = document.querySelector('.nav-badge');
        if (navBadge) {
            const navCount = parseInt(navBadge.textContent, 10);
            if (!Number.isNaN(navCount)) {
                const nextNavCount = Math.max(0, navCount - 1);
                if (nextNavCount > 0) {
                    navBadge.textContent = String(nextNavCount);
                } else {
                    navBadge.remove();
                }
            }
        }
    }

    function getCsrfToken() {
        const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function closeMessage() {
        const modal = document.getElementById('messageModal');
        if (modal) {
            modal.classList.remove('show');
        }
    }

    const messageModal = document.getElementById('messageModal');
    const openMessageButtons = Array.from(document.querySelectorAll('[data-open-message]'));
    const closeMessageButtons = Array.from(document.querySelectorAll('[data-close-message]'));
    const confirmButtons = Array.from(document.querySelectorAll('button[data-confirm], input[type="submit"][data-confirm]'));

    if (!messageModal && !openMessageButtons.length && !closeMessageButtons.length && !confirmButtons.length) {
        return;
    }

    openMessageButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            const id = Number(button.getAttribute('data-message-id') || '0');
            const name = button.getAttribute('data-name') || '';
            const email = button.getAttribute('data-email') || '';
            const phone = button.getAttribute('data-phone') || '';
            const subject = button.getAttribute('data-subject') || '';
            const message = button.getAttribute('data-message') || '';
            const isUnread = (button.getAttribute('data-is-unread') || '').toLowerCase() === 'true';
            openMessage(id, name, email, phone, subject, message, isUnread);
        });
    });

    closeMessageButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            closeMessage();
        });
    });

    confirmButtons.forEach(function (button) {
        button.addEventListener('click', function (event) {
            const message = button.getAttribute('data-confirm');
            if (!message) {
                return;
            }
            if (!window.confirm(message)) {
                event.preventDefault();
                event.stopPropagation();
            }
        });
    });

    // Cerrar al hacer click fuera
    window.addEventListener('click', function(event) {
        if (event.target === messageModal) {
            closeMessage();
        }
    });
})();
/* ===== end contact_messages_admin.html :: script 1 ===== */

/* ===== edit_stock.html :: script 1 ===== */
(function () {
        const fileField = document.querySelector('.file-field');
        if (!fileField) {
            return;
        }

        const clearCheckbox = fileField.querySelector('input[type="checkbox"][id$="-clear_id"]');
        if (!clearCheckbox) {
            return;
        }

        const clearLabel = fileField.querySelector('label[for="' + clearCheckbox.id + '"]');
        if (!clearLabel || clearCheckbox.parentElement.classList.contains('clear-photo-row')) {
            return;
        }

        const row = document.createElement('div');
        row.className = 'clear-photo-row';
        clearCheckbox.parentNode.insertBefore(row, clearCheckbox);
        row.appendChild(clearCheckbox);
        row.appendChild(clearLabel);
    })();

    (function () {
        const list = document.getElementById('gallery-list-sortable');
        if (!list) {
            return;
        }

        function getItems() {
            return Array.from(list.querySelectorAll('.gallery-item'));
        }

        function syncOrderInputs() {
            getItems().forEach(function (item, index) {
                const input = item.querySelector('input[name^="order_image_"]');
                if (input) {
                    input.value = index + 1;
                }
            });
            updateMoveButtons();
        }

        function updateMoveButtons() {
            const items = getItems();
            items.forEach(function (item, index) {
                const upBtn = item.querySelector('.move-up');
                const downBtn = item.querySelector('.move-down');
                if (upBtn) {
                    upBtn.disabled = index === 0;
                }
                if (downBtn) {
                    downBtn.disabled = index === items.length - 1;
                }
            });
        }

        let draggingItem = null;

        function clearDropTargets() {
            getItems().forEach(function (item) {
                item.classList.remove('drop-target');
            });
        }

        list.addEventListener('dragstart', function (event) {
            const item = event.target.closest('.gallery-item');
            if (!item) {
                return;
            }
            draggingItem = item;
            item.classList.add('dragging');
            event.dataTransfer.effectAllowed = 'move';
        });

        list.addEventListener('dragend', function () {
            if (draggingItem) {
                draggingItem.classList.remove('dragging');
            }
            clearDropTargets();
            draggingItem = null;
            syncOrderInputs();
        });

        list.addEventListener('dragover', function (event) {
            if (!draggingItem) {
                return;
            }
            event.preventDefault();
            const target = event.target.closest('.gallery-item');
            if (!target || target === draggingItem) {
                return;
            }

            clearDropTargets();
            target.classList.add('drop-target');

            const rect = target.getBoundingClientRect();
            const shouldInsertAfter = event.clientY > rect.top + rect.height / 2;
            if (shouldInsertAfter) {
                target.after(draggingItem);
            } else {
                target.before(draggingItem);
            }
        });

        list.addEventListener('drop', function (event) {
            event.preventDefault();
            clearDropTargets();
            syncOrderInputs();
        });

        list.addEventListener('click', function (event) {
            const upButton = event.target.closest('.move-up');
            const downButton = event.target.closest('.move-down');
            const item = event.target.closest('.gallery-item');

            if (!item) {
                return;
            }

            if (upButton) {
                const previous = item.previousElementSibling;
                if (previous) {
                    previous.before(item);
                    syncOrderInputs();
                }
                return;
            }

            if (downButton) {
                const next = item.nextElementSibling;
                if (next) {
                    next.after(item);
                    syncOrderInputs();
                }
            }
        });

        syncOrderInputs();
    })();
/* ===== end edit_stock.html :: script 1 ===== */

/* ===== favorites.html :: script 1 ===== */
(function () {
        const compareButton = document.getElementById('fav-compare-btn');
        const compareInfo = document.getElementById('fav-compare-info');
        const checkboxes = Array.from(document.querySelectorAll('.compare-checkbox'));

        if (!compareButton || !compareInfo || !checkboxes.length) {
            return;
        }

        function getSelectedIds() {
            return checkboxes
                .filter(function (cb) { return cb.checked; })
                .map(function (cb) { return cb.value; });
        }

        function renderCompareState() {
            const selected = getSelectedIds();
            const count = selected.length;

            compareInfo.textContent = count > 0
                ? count + ' seleccionado(s). Máximo 3.'
                : 'Selecciona 2 o 3 favoritos para comparar';

            if (count >= 2 && count <= 3) {
                compareButton.classList.remove('disabled');
                compareButton.setAttribute('aria-disabled', 'false');
                compareButton.href = '/comparar/?' + selected.map(function (id) {
                    return 'ids=' + encodeURIComponent(id);
                }).join('&');
            } else {
                compareButton.classList.add('disabled');
                compareButton.setAttribute('aria-disabled', 'true');
                compareButton.href = '/comparar/';
            }
        }

        checkboxes.forEach(function (checkbox) {
            checkbox.addEventListener('change', function () {
                const selectedCount = getSelectedIds().length;
                if (selectedCount > 3) {
                    checkbox.checked = false;
                }
                renderCompareState();
            });
        });

        renderCompareState();
    })();
/* ===== end favorites.html :: script 1 ===== */

/* ===== index.html :: script 1 ===== */
(function () {
		const hero = document.getElementById('hero');
		const heroHighlight = document.getElementById('hero-highlight');
		const prevBtn = document.getElementById('hero-prev');
		const nextBtn = document.getElementById('hero-next');
		const dotsContainer = document.getElementById('hero-dots');
		const dots = dotsContainer ? dotsContainer.querySelectorAll('.hero-dot') : [];
		const featuredNode = document.getElementById('featured-hero-data');
		const featured = featuredNode ? JSON.parse(featuredNode.textContent) : [];

        if (hero) {
            const initialHeroPhoto = hero.getAttribute('data-hero-photo');
            if (initialHeroPhoto) {
                hero.style.backgroundImage = "linear-gradient(rgba(17, 24, 39, 0.72), rgba(31, 41, 55, 0.82)), url('" + initialHeroPhoto + "')";
                hero.style.backgroundSize = 'cover';
                hero.style.backgroundPosition = 'center';
            }
        }

		if (hero && featured.length > 1) {
			let index = 0;
			const gradientOnly = 'linear-gradient(135deg, #111827, #1f2937)';
			let rotationTimer = null;
			let touchStartX = 0;
			let touchStartY = 0;

			function paintHero(item) {
				if (item.photo) {
					hero.style.backgroundImage = `linear-gradient(rgba(17, 24, 39, 0.72), rgba(31, 41, 55, 0.82)), url('${item.photo}')`;
					hero.style.backgroundSize = 'cover';
					hero.style.backgroundPosition = 'center';
				} else {
					hero.style.backgroundImage = gradientOnly;
					hero.style.backgroundSize = '';
					hero.style.backgroundPosition = '';
				}

				if (heroHighlight) {
					heroHighlight.textContent = `Destacado: ${item.title} · ${item.price}`;
				}

				dots.forEach(function (dot, dotIndex) {
					dot.classList.toggle('active', dotIndex === index);
				});
			}

			function showByIndex(newIndex) {
				index = (newIndex + featured.length) % featured.length;
				paintHero(featured[index]);
			}

			function startRotation() {
				if (rotationTimer) {
					return;
				}
				rotationTimer = setInterval(function () {
					showByIndex(index + 1);
				}, 5000);
			}

			function stopRotation() {
				if (!rotationTimer) {
					return;
				}
				clearInterval(rotationTimer);
				rotationTimer = null;
			}

			if (prevBtn) {
				prevBtn.addEventListener('click', function () {
					showByIndex(index - 1);
				});
			}

			if (nextBtn) {
				nextBtn.addEventListener('click', function () {
					showByIndex(index + 1);
				});
			}

			dots.forEach(function (dot) {
				dot.addEventListener('click', function () {
					const targetIndex = Number(dot.getAttribute('data-index'));
					showByIndex(targetIndex);
				});
			});

			hero.addEventListener('mouseenter', stopRotation);
			hero.addEventListener('mouseleave', startRotation);
			hero.addEventListener('touchstart', function (event) {
				const touch = event.changedTouches && event.changedTouches[0];
				if (!touch) {
					return;
				}
				touchStartX = touch.clientX;
				touchStartY = touch.clientY;
				stopRotation();
			}, { passive: true });

			hero.addEventListener('touchend', function (event) {
				const touch = event.changedTouches && event.changedTouches[0];
				if (!touch) {
					startRotation();
					return;
				}

				const deltaX = touch.clientX - touchStartX;
				const deltaY = touch.clientY - touchStartY;
				const absX = Math.abs(deltaX);
				const absY = Math.abs(deltaY);

				if (absX > 45 && absX > absY) {
					if (deltaX < 0) {
						showByIndex(index + 1);
					} else {
						showByIndex(index - 1);
					}
				}

				startRotation();
			}, { passive: true });
			hero.addEventListener('touchcancel', startRotation, { passive: true });

			startRotation();
		}

		const reviewsTrack = document.getElementById('reviews-track');
		const reviewsPrev = document.getElementById('reviews-prev');
		const reviewsNext = document.getElementById('reviews-next');
		const reviewsDotsContainer = document.getElementById('reviews-dots');
		const reviewCards = reviewsTrack ? Array.from(reviewsTrack.querySelectorAll('.review-card')) : [];

		if (reviewsTrack && reviewCards.length > 0) {
			let reviewIndex = 0;
			let reviewsAutoplayTimer = null;
			let reviewPages = [0];
			let reviewDots = [];

			function getReviewStep() {
				if (reviewCards.length > 1) {
					return reviewCards[1].offsetLeft - reviewCards[0].offsetLeft;
				}
				return reviewCards[0].getBoundingClientRect().width;
			}

			function getVisibleCards() {
				const step = getReviewStep();
				if (!step) {
					return 1;
				}

				return Math.max(1, Math.round(reviewsTrack.clientWidth / step));
			}

			function buildReviewPages() {
				const visibleCards = getVisibleCards();
				const pages = [];

				for (let index = 0; index < reviewCards.length; index += visibleCards) {
					pages.push(index);
				}

				if (!pages.length) {
					pages.push(0);
				}

				reviewPages = pages;
			}

			function renderReviewDots() {
				if (!reviewsDotsContainer) {
					return;
				}

				reviewsDotsContainer.innerHTML = '';
				reviewDots = reviewPages.map(function (pageStart, pageIndex) {
					const dot = document.createElement('button');
					dot.type = 'button';
					dot.className = 'review-dot';
					dot.setAttribute('data-index', String(pageStart));
					dot.setAttribute('aria-label', `Ir al grupo de reseñas ${pageIndex + 1}`);
					dot.addEventListener('click', function () {
						stopReviewsAutoplay();
						goToReview(pageStart);
						startReviewsAutoplay();
					});
					reviewsDotsContainer.appendChild(dot);
					return dot;
				});
			}

			function getActiveReviewPage() {
				let activePage = 0;
				for (let pageIndex = 0; pageIndex < reviewPages.length; pageIndex += 1) {
					if (reviewIndex >= reviewPages[pageIndex]) {
						activePage = pageIndex;
					} else {
						break;
					}
				}
				return activePage;
			}

			function syncReviewDots() {
				const activePage = getActiveReviewPage();
				reviewDots.forEach(function (dot, dotIndex) {
					dot.classList.toggle('active', dotIndex === activePage);
				});
			}

			function goToReview(newIndex) {
				reviewIndex = (newIndex + reviewCards.length) % reviewCards.length;
				reviewsTrack.scrollTo({
					left: getReviewStep() * reviewIndex,
					behavior: 'smooth'
				});
				syncReviewDots();
			}

			function stopReviewsAutoplay() {
				if (!reviewsAutoplayTimer) {
					return;
				}

				clearInterval(reviewsAutoplayTimer);
				reviewsAutoplayTimer = null;
			}

			function startReviewsAutoplay() {
				if (reviewCards.length < 2 || reviewsAutoplayTimer) {
					return;
				}

				reviewsAutoplayTimer = setInterval(function () {
					goToReview(reviewIndex + 1);
				}, 4200);
			}

			if (reviewsPrev) {
				reviewsPrev.addEventListener('click', function () {
					stopReviewsAutoplay();
					goToReview(reviewPages[(getActiveReviewPage() - 1 + reviewPages.length) % reviewPages.length]);
					startReviewsAutoplay();
				});
			}

			if (reviewsNext) {
				reviewsNext.addEventListener('click', function () {
					stopReviewsAutoplay();
					goToReview(reviewPages[(getActiveReviewPage() + 1) % reviewPages.length]);
					startReviewsAutoplay();
				});
			}

			reviewsTrack.addEventListener('scroll', function () {
				const step = getReviewStep();
				if (!step) {
					return;
				}
				reviewIndex = Math.max(0, Math.min(Math.round(reviewsTrack.scrollLeft / step), reviewCards.length - 1));
				syncReviewDots();
			}, { passive: true });

			window.addEventListener('resize', function () {
				buildReviewPages();
				renderReviewDots();
				goToReview(reviewIndex);
			});

			reviewsTrack.addEventListener('mouseenter', stopReviewsAutoplay);
			reviewsTrack.addEventListener('mouseleave', startReviewsAutoplay);
			reviewsTrack.addEventListener('touchstart', stopReviewsAutoplay, { passive: true });
			reviewsTrack.addEventListener('touchend', startReviewsAutoplay, { passive: true });
			reviewsTrack.addEventListener('touchcancel', startReviewsAutoplay, { passive: true });

			buildReviewPages();
			renderReviewDots();
			syncReviewDots();
			startReviewsAutoplay();
		}
	})();
/* ===== end index.html :: script 1 ===== */

/* ===== item_page.html :: script 1 ===== */
(function () {
        const mainPhoto = document.getElementById('main-photo');
        const thumbStrip = document.getElementById('thumb-strip');

        if (!mainPhoto || !thumbStrip) {
            return;
        }

        const thumbs = Array.from(thumbStrip.querySelectorAll('.thumb-btn'));
        thumbs.forEach(function (thumb) {
            thumb.addEventListener('click', function () {
                const newImage = thumb.getAttribute('data-image');
                if (!newImage) {
                    return;
                }

                mainPhoto.src = newImage;
                thumbs.forEach(function (item) {
                    item.classList.remove('active');
                });
                thumb.classList.add('active');
            });
        });
    })();

    (function () {
        const form = document.querySelector('.test-drive-form');
        const dayInput = document.getElementById('td-day');
        const timeSelect = document.getElementById('td-time');
        const helpText = document.getElementById('td-help');

        if (!form || !dayInput || !timeSelect) {
            return;
        }

        const today = new Date();
        const tzOffsetMs = today.getTimezoneOffset() * 60 * 1000;
        const localTodayIso = new Date(today.getTime() - tzOffsetMs).toISOString().slice(0, 10);
        dayInput.min = localTodayIso;

        const selectedTime = timeSelect.getAttribute('data-selected') || '';

        function setTimeOptions(slots, preferredValue) {
            timeSelect.innerHTML = '';

            if (!slots.length) {
                const noOption = document.createElement('option');
                noOption.value = '';
                noOption.textContent = 'Sin disponibilidad para esta fecha';
                timeSelect.appendChild(noOption);
                return;
            }

            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Selecciona una hora';
            timeSelect.appendChild(placeholder);

            slots.forEach(function (slot) {
                const option = document.createElement('option');
                option.value = slot;
                option.textContent = slot;
                if (preferredValue && preferredValue === slot) {
                    option.selected = true;
                }
                timeSelect.appendChild(option);
            });
        }

        async function loadSlotsForDate(dateValue, preferredValue) {
            if (!dateValue) {
                setTimeOptions([], '');
                return;
            }

            const endpoint = form.getAttribute('data-slots-url');
            if (!endpoint) {
                return;
            }

            try {
                const response = await fetch(endpoint + '?date=' + encodeURIComponent(dateValue));
                const payload = await response.json();
                setTimeOptions(Array.isArray(payload.slots) ? payload.slots : [], preferredValue || '');

                if (helpText) {
                    if (payload.closed && payload.is_sunday) {
                        helpText.textContent = 'Domingo cerrado. Selecciona otro día.';
                    } else if (payload.closed && payload.is_holiday) {
                        helpText.textContent = 'Festivo cerrado. Selecciona otra fecha.';
                    } else {
                        helpText.textContent = 'Horario comercial: L-V 09:30–20:00 · Sáb 10:00–16:00 · Domingo y festivos cerrado.';
                    }
                }
            } catch (error) {
                setTimeOptions([], '');
            }
        }

        dayInput.addEventListener('change', function () {
            loadSlotsForDate(dayInput.value, '');
        });

        if (dayInput.value) {
            loadSlotsForDate(dayInput.value, selectedTime);
        }
    })();

    (function () {
        const card = document.querySelector('.finance-card[data-price]');
        const entryInput = document.getElementById('fin-entry');
        const monthsInput = document.getElementById('fin-months');
        const rateInput = document.getElementById('fin-rate');
        const resultNode = document.getElementById('fin-result');

        if (!card || !entryInput || !monthsInput || !rateInput || !resultNode) {
            return;
        }

        const price = Number(card.getAttribute('data-price') || '0');
        if (!price || price <= 0) {
            return;
        }

        function monthlyPayment(principal, annualRatePercent, totalMonths) {
            if (principal <= 0 || totalMonths <= 0) {
                return 0;
            }

            const monthlyRate = (annualRatePercent / 100) / 12;
            if (monthlyRate <= 0) {
                return principal / totalMonths;
            }

            return (principal * monthlyRate) / (1 - Math.pow(1 + monthlyRate, -totalMonths));
        }

        function render() {
            const entry = Math.max(0, Number(entryInput.value || '0'));
            const months = Math.max(1, Number(monthsInput.value || '60'));
            const rate = Math.max(0, Number(rateInput.value || '0'));
            const financed = Math.max(0, price - entry);
            const monthly = monthlyPayment(financed, rate, months);
            const formatted = Math.round(monthly).toLocaleString('es-ES');
            resultNode.innerHTML = 'Cuota estimada: <strong>' + formatted + ' €/mes</strong>';
        }

        [entryInput, monthsInput, rateInput].forEach(function (node) {
            node.addEventListener('input', render);
            node.addEventListener('change', render);
        });

        render();
    })();

    (function () {
        const copyButton = document.getElementById('copy-share-link');
        const feedback = document.getElementById('share-feedback');

        if (!copyButton) {
            return;
        }

        copyButton.addEventListener('click', async function () {
            const shareUrl = copyButton.getAttribute('data-url');
            if (!shareUrl) {
                return;
            }

            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(shareUrl);
                } else {
                    const tempInput = document.createElement('input');
                    tempInput.value = shareUrl;
                    document.body.appendChild(tempInput);
                    tempInput.select();
                    document.execCommand('copy');
                    document.body.removeChild(tempInput);
                }

                if (feedback) {
                    feedback.textContent = 'Enlace copiado al portapapeles.';
                }
            } catch (error) {
                if (feedback) {
                    feedback.textContent = 'No se pudo copiar el enlace.';
                }
            }
        });
    })();
/* ===== end item_page.html :: script 1 ===== */

/* ===== stock.html :: script 1 ===== */
(function () {
        const toggleBtn = document.getElementById('stock-toggle-btn');
        const filtersWrapper = document.getElementById('stock-filters');

        if (!toggleBtn || !filtersWrapper) {
            return;
        }

        const storageKey = 'autolux_stock_filters_expanded';
        const isExpandedInStorage = localStorage.getItem(storageKey) === 'true';

        function setFiltersState(expanded) {
            if (expanded) {
                filtersWrapper.classList.remove('collapsed');
                toggleBtn.setAttribute('aria-expanded', 'true');
            } else {
                filtersWrapper.classList.add('collapsed');
                toggleBtn.setAttribute('aria-expanded', 'false');
            }
            localStorage.setItem(storageKey, String(expanded));
        }

        toggleBtn.addEventListener('click', function (e) {
            e.preventDefault();
            const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
            setFiltersState(!isExpanded);
        });

        setFiltersState(isExpandedInStorage);
    })();

    (function () {
        const compareButton = document.getElementById('compare-button');
        const compareInfo = document.getElementById('compare-info');
        const checkboxes = Array.from(document.querySelectorAll('.compare-checkbox'));

        if (!compareButton || !compareInfo || !checkboxes.length) {
            return;
        }

        function getSelectedIds() {
            return checkboxes
                .filter(function (cb) { return cb.checked; })
                .map(function (cb) { return cb.value; });
        }

        function renderCompareState() {
            const selected = getSelectedIds();
            const count = selected.length;

            compareInfo.textContent = count > 0
                ? count + ' seleccionado(s). Máximo 3.'
                : 'Selecciona 2 o 3 vehículos para comparar';

            if (count >= 2 && count <= 3) {
                compareButton.classList.remove('disabled');
                compareButton.setAttribute('aria-disabled', 'false');
                compareButton.href = '/comparar/?' + selected.map(function (id) {
                    return 'ids=' + encodeURIComponent(id);
                }).join('&');
            } else {
                compareButton.classList.add('disabled');
                compareButton.setAttribute('aria-disabled', 'true');
                compareButton.href = '/comparar/';
            }
        }

        checkboxes.forEach(function (checkbox) {
            checkbox.addEventListener('change', function () {
                const selectedCount = getSelectedIds().length;
                if (selectedCount > 3) {
                    checkbox.checked = false;
                }
                renderCompareState();
            });
        });

        renderCompareState();
    })();
/* ===== end stock.html :: script 1 ===== */
