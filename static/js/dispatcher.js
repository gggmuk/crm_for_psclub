document.addEventListener('DOMContentLoaded', () => {
    const placesGrid = document.getElementById('places-grid');
    const refreshButton = document.querySelector('button'); // Assuming the first button is refresh for now, or add an ID

    async function fetchPlaces() {
        try {
            const response = await fetch('/api/place_status/');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const places = await response.json();
            renderPlaces(places);
        } catch (error) {
            console.error('Error fetching places:', error);
            placesGrid.innerHTML = '<p class="text-red-500 col-span-full text-center">Ошибка загрузки данных</p>';
        }
    }

    function renderPlaces(places) {
        placesGrid.innerHTML = ''; // Clear existing content

        places.forEach(place => {
            const tile = createPlaceTile(place);
            placesGrid.appendChild(tile);
        });
    }

    function createPlaceTile(place) {
        const div = document.createElement('div');

        // Base classes
        let classes = 'rounded-xl border p-5 transition-all cursor-pointer group relative overflow-hidden';
        let statusBadgeClass = '';
        let statusText = '';
        let buttonHtml = '';
        let borderColor = '';

        // Determine styles based on status
        switch (place.status) {
            case 'free':
                classes += ' bg-gray-800 border-gray-700 hover:border-gray-600';
                statusBadgeClass = 'bg-green-900/30 text-green-400 border-green-900/50';
                statusText = 'Свободно';
                borderColor = 'border-gray-700';
                buttonHtml = `
                    <button class="w-full py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors group-hover:bg-blue-600" onclick="startSession(${place.id})">
                        Начать сессию
                    </button>`;
                break;
            case 'occupied':
                classes += ' bg-gray-800 border-blue-900/50 hover:border-blue-800';
                statusBadgeClass = 'bg-blue-900/30 text-blue-400 border-blue-900/50';
                statusText = 'Занято';
                borderColor = 'border-blue-900/50';
                buttonHtml = `
                    <button class="w-full py-2 bg-red-900/20 hover:bg-red-900/40 text-red-400 border border-red-900/30 text-sm font-medium rounded-lg transition-colors mt-2 relative z-10" onclick="stopSession(${place.id})">
                        Завершить
                    </button>`;
                break;
            case 'maintenance':
                classes += ' bg-gray-800/50 border-gray-700 opacity-75 cursor-not-allowed';
                statusBadgeClass = 'bg-yellow-900/20 text-yellow-600 border-yellow-900/30';
                statusText = 'Ремонт';
                borderColor = 'border-gray-700';
                buttonHtml = `
                    <button class="w-full py-2 bg-gray-800 text-gray-600 text-sm font-medium rounded-lg cursor-not-allowed" disabled>
                        Недоступно
                    </button>`;
                break;
            default:
                classes += ' bg-gray-800 border-gray-700';
                statusText = 'Неизвестно';
        }

        div.className = classes;

        div.innerHTML = `
            <div class="flex justify-between items-start mb-4 relative z-10">
                <span class="text-lg font-bold text-white">${place.name}</span>
                <span class="px-2 py-1 rounded-full text-xs font-medium border ${statusBadgeClass}">${statusText}</span>
            </div>
            <div class="text-sm text-gray-400 mb-4 relative z-10">
                <p>${place.status === 'occupied' ? 'Сессия активна' : 'Стандарт'}</p>
            </div>
            ${buttonHtml}
        `;

        return div;
    }

    // Initial load
    fetchPlaces();

    // Attach refresh handler if button exists
    if (refreshButton) {
        refreshButton.addEventListener('click', fetchPlaces);
    }
});

// Modal Logic
const modal = document.getElementById('startSessionModal');
const modalPlaceIdInput = document.getElementById('modalPlaceId');
const startSessionForm = document.getElementById('startSessionForm');

function startSession(placeId) {
    modalPlaceIdInput.value = placeId;
    modal.classList.remove('hidden');
    document.getElementById('clientId').focus();
}

function closeModal() {
    modal.classList.add('hidden');
    startSessionForm.reset();
}

// Close modal on outside click
modal.addEventListener('click', (e) => {
    if (e.target === modal) {
        closeModal();
    }
});

// Handle Form Submission
startSessionForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const placeId = modalPlaceIdInput.value;
    const clientId = document.getElementById('clientId').value;
    const submitBtn = startSessionForm.querySelector('button[type="submit"]');

    // Loading state
    const originalBtnText = submitBtn.innerText;
    submitBtn.innerText = 'Загрузка...';
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/start_session/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // 'X-CSRFToken': getCookie('csrftoken') // Ensure you handle CSRF in real app
            },
            body: JSON.stringify({
                place_id: placeId,
                client_id: clientId
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка при создании сессии');
        }

        // Success
        closeModal();
        // Refresh the grid
        const refreshButton = document.querySelector('button'); // Re-select or expose fetchPlaces
        if (refreshButton) refreshButton.click();

        // Ideally call fetchPlaces() directly if exposed, but triggering click works for now
        // or dispatch a custom event

    } catch (error) {
        alert(error.message);
    } finally {
        submitBtn.innerText = originalBtnText;
        submitBtn.disabled = false;
    }
});

function stopSession(placeId) {
    if (!confirm('Вы уверены, что хотите завершить сессию?')) return;

    // Logic to call stop session API would go here
    console.log('Stop session for place:', placeId);
}
