require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const QRCode = require('qrcode');

// ============== Конфигурация ==============
const token = process.env.BOT_TOKEN;
const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000/api';
const API_KEY = process.env.CRM_API_KEY || '';

function apiHeaders() {
    const h = {};
    if (API_KEY) h['X-API-Key'] = API_KEY;
    return h;
}

if (!token || token === 'YOUR_TELEGRAM_BOT_TOKEN_HERE') {
    console.error('❌ BOT_TOKEN не указан в .env');
    process.exit(1);
}

const bot = new TelegramBot(token, { polling: true });
// Храним состояния: WAIT_NAME, BOOKING_PLACE, BOOKING_DUR
const userStates = {};

console.log('🚀 CyberLounge Bot запущен | API:', API_BASE_URL);

// ============== API Помощники ==============

async function apiWithRetry(fn, retries = 3) {
    for (let i = 0; i < retries; i++) {
        try { 
            return await fn(); 
        } catch (e) {
            if (i < retries - 1 && (e.code === 'ECONNREFUSED' || e.code === 'ECONNABORTED' || !e.response)) {
                await new Promise(r => setTimeout(r, 2000));
            } else throw e;
        }
    }
}

async function apiGet(path) {
    return apiWithRetry(() => axios.get(`${API_BASE_URL}${path}`, { timeout: 3000, headers: apiHeaders() }).then(r => r.data));
}

async function apiPost(path, data) {
    return apiWithRetry(() => axios.post(`${API_BASE_URL}${path}`, data, { timeout: 5000, headers: apiHeaders() }).then(r => r.data));
}

async function apiPatch(path, data) {
    return apiWithRetry(() => axios.patch(`${API_BASE_URL}${path}`, data || {}, { timeout: 5000, headers: apiHeaders() }).then(r => r.data));
}

async function getClient(telegramId) {
    try {
        return await apiGet(`/client_info/${telegramId}/`);
    } catch (e) {
        if (e.response && e.response.status === 404) return null;
        throw e;
    }
}

// ============== Генерация QR ==============

async function generateQRBuffer(data) {
    return await QRCode.toBuffer(JSON.stringify(data), {
        width: 400, margin: 2, color: { dark: '#000000', light: '#ffffff' }
    });
}

// ============== Клавиатуры ==============

function mainKeyboard() {
    return {
        reply_markup: {
            keyboard: [
                ['🎮 Статус клуба', '👤 Мой профиль'],
                ['📅 Забронировать', '📋 Мои брони'],
                ['🎁 Рефералка', '🆔 Мой QR-код'],
            ],
            resize_keyboard: true
        }
    };
}

function cancelKeyboard() {
    return {
        reply_markup: {
            keyboard: [['❌ Отмена']],
            resize_keyboard: true
        }
    };
}

// ============== Обработчик /start ==============

bot.onText(/\/start(.*)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const referralParam = match[1] ? match[1].trim() : '';
    delete userStates[chatId]; // сброс состояния

    try {
        const client = await getClient(chatId);
        if (client) {
            const text = `*С возвращением, ${client.name}!* 👋\n\nИспользуй меню внизу 👇`;
            bot.sendMessage(chatId, text, { parse_mode: 'Markdown', ...mainKeyboard() });
        } else {
            userStates[chatId] = { step: 'WAIT_NAME', referral: referralParam };
            bot.sendMessage(chatId,
                '🎮 *Добро пожаловать в CyberLounge!*\n\nМы — PlayStation клуб нового поколения.\n' +
                '✍️ *Как тебя зовут?*',
                { parse_mode: 'Markdown', reply_markup: { remove_keyboard: true } }
            );
        }
    } catch (error) {
        bot.sendMessage(chatId, '❌ Ошибка при соединении с сервером. Попробуйте позже.');
    }
});

// ============== Полнотекстовые сообщения ==============

bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;

    if (!text || text.startsWith('/')) return;

    const state = userStates[chatId] || {};

    // ОБРАБОТКА: Отмена
    if (text === '❌ Отмена' || text === 'Отмена') {
        delete userStates[chatId];
        return bot.sendMessage(chatId, 'Возвращаемся в главное меню.', mainKeyboard());
    }

    // ОБРАБОТКА: Регистрация (Ожидание имени)
    if (state.step === 'WAIT_NAME') {
        const referral = state.referral;
        delete userStates[chatId];
        try {
            await apiPost('/register_client/', { telegram_id: chatId, name: text, referral_code: referral || undefined });
            return bot.sendMessage(chatId, `🎉 Отлично, ${text}! Вы успешно зарегистрированы.`, mainKeyboard());
        } catch (error) {
            return bot.sendMessage(chatId, '❌ Произошла ошибка регистрации. Попробуйте еще раз: /start');
        }
    }

    // ПРОВЕРКА: Зарегистрирован ли клиент?
    let client = null;
    try { client = await getClient(chatId); } catch(e){}

    if (!client && !['❌ Отмена'].includes(text)) {
        return; // Игнорируем обычный текст для незарегистрированных (они должны нажать /start)
    }

    // ОБРАБОТКА: Выбор комнаты (Шаг 2 -> Шаг 3: Выбор дня)
    if (state.step === 'BOOKING_PLACE' && text.startsWith('📍 ')) {
        const match = text.match(/\(ID:\s*(\d+)\)/i);
        if (match) {
            const placeId = parseInt(match[1]);
            userStates[chatId] = { step: 'BOOKING_DAY', placeId: placeId };
            
            const dayKeyboard = {
                reply_markup: {
                    keyboard: [
                        ['📅 Сегодня', '📅 Завтра'],
                        ['❌ Отмена']
                    ],
                    resize_keyboard: true
                }
            };
            return bot.sendMessage(chatId, `Выбрана комната.\n🗓 *Когда планируете прийти?*`, { parse_mode: 'Markdown', ...dayKeyboard });
        }
    }

    // ОБРАБОТКА: Выбор дня (Шаг 3 -> Шаг 4: Выбор времени)
    if (state.step === 'BOOKING_DAY' && text.startsWith('📅 ')) {
        const isTomorrow = text.includes('Завтра');
        userStates[chatId].isTomorrow = isTomorrow;
        userStates[chatId].step = 'BOOKING_TIME';

        // Генерируем доступные часы
        const now = new Date();
        const startHour = isTomorrow ? 10 : Math.max(10, now.getHours() + 1); // Клуб с 10:00 (условно) или со следующего часа
        
        const timeKeyboard = [];
        let currentRow = [];
        for (let h = startHour; h <= 23; h++) {
            currentRow.push(`⏰ ${h}:00`);
            if (currentRow.length === 3) {
                timeKeyboard.push(currentRow);
                currentRow = [];
            }
        }
        if (currentRow.length > 0) timeKeyboard.push(currentRow);
        if (timeKeyboard.length === 0) timeKeyboard.push(['📅 Выбрать другой день']);
        timeKeyboard.push(['❌ Отмена']);

        return bot.sendMessage(chatId, `День выбран.\n⏳ *Во сколько начнется сессия?*`, { 
            parse_mode: 'Markdown', 
            reply_markup: { keyboard: timeKeyboard, resize_keyboard: true }
        });
    }

    // ОБРАБОТКА: Выбор времени (Шаг 4 -> Шаг 5: Выбор длительности)
    if (state.step === 'BOOKING_TIME' && text.startsWith('⏰ ')) {
        const match = text.match(/(\d{1,2}):(\d{2})/);
        if (match) {
            userStates[chatId].selectedHour = parseInt(match[1]);
            userStates[chatId].selectedMinute = parseInt(match[2]);
            userStates[chatId].step = 'BOOKING_DUR';
            
            const durKeyboard = {
                reply_markup: {
                    keyboard: [
                        ['⏱ 1 час', '⏱ 2 часа', '⏱ 3 часа'],
                        ['⏱ 4 часа', '⏱ 5 часов', '❌ Отмена']
                    ],
                    resize_keyboard: true
                }
            };
            return bot.sendMessage(chatId, `Время выбрано.\n⏳ *На сколько часов бронируем?*`, { parse_mode: 'Markdown', ...durKeyboard });
        }
    }

    // ОБРАБОТКА: Выбор длительности (ФИНАЛ)
    if (state.step === 'BOOKING_DUR' && text.startsWith('⏱ ')) {
        const match = text.match(/\d+/);
        if (match) {
            const hours = parseInt(match[0]);
            
            const placeId = state.placeId;
            const isTomorrow = state.isTomorrow;
            let selHour = state.selectedHour;
            let selMin = state.selectedMinute;

            delete userStates[chatId];

            try {
                const start = new Date();
                if (isTomorrow) start.setDate(start.getDate() + 1);
                start.setHours(selHour, selMin, 0, 0);

                // Если время каким-то чудом меньше текущего (например, сегодня и выбрали прошедший час - ставим +10 мин)
                if (start < new Date()) {
                    start.setTime(new Date().getTime() + 10 * 60000);
                    selHour = start.getHours();
                    selMin = start.getMinutes();
                }

                const end = new Date(start.getTime() + hours * 3600000);

                // Отправляем ISO с таймзоной (toISOString = UTC), бэкенд примет aware-дату
                const fmt = (d) => d.toISOString();

                await apiPost('/create_booking/', { telegram_id: chatId, place_id: placeId, start_time: fmt(start), end_time: fmt(end) });

                const timeStr = String(start.getHours()).padStart(2,'0') + ':' + String(start.getMinutes()).padStart(2,'0');
                const dateStr = start.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });

                return bot.sendMessage(chatId, 
                    `✅ *Бронь успешно создана!*\n\n📍 Комната №${placeId}\n📅 Дата: ${dateStr}\n⏰ Начало: ${timeStr}\n⏳ Длительность: ${hours}ч\n\n_Ожидайте подтверждения от администратора._`,
                    { parse_mode: 'Markdown', ...mainKeyboard() }
                );
            } catch (error) {
                const errMsg = error.response?.data?.error || 'Неизвестная ошибка';
                return bot.sendMessage(chatId, `❌ Ошибка бронирования: ${errMsg}`, mainKeyboard());
            }
        }
    }
    
    // ОБРАБОТКА: Отмена броней
    if (text.startsWith('🗑 Отменить бронь ')) {
        const match = text.match(/ID:\s*(\d+)/i);
        if (match) {
            const bookingId = parseInt(match[1]);
            try {
                await apiPatch(`/cancel_booking/${bookingId}/`, { status: 'canceled' });
                return bot.sendMessage(chatId, '✅ Бронь отменена.', mainKeyboard());
            } catch (error) {
                return bot.sendMessage(chatId, '❌ Не удалось отменить бронь.', mainKeyboard());
            }
        }
    }

    // ---------------- МЕНЮ ----------------

    if (text === '🎮 Статус клуба') {
        try {
            const places = await apiGet('/place_status/');
            const freePlaces = places.filter(p => p.status === 'free');
            const occupiedPlaces = places.filter(p => p.status === 'occupied');
            
            let statusText = '🎮 *CyberLounge — Карта клуба*\n\n';
            const types = {};
            places.forEach(p => {
                const type = p.place_type || 'Standard';
                if (!types[type]) types[type] = [];
                types[type].push(p);
            });

            for (const [type, list] of Object.entries(types)) {
                const typeIcon = type === 'VIP' ? '👑' : '🎮';
                statusText += `${typeIcon} *${type}:*\n`;
                list.forEach(p => {
                    const icon = p.status === 'free' ? '🟢' : p.status === 'occupied' ? '🔴' : '🔧';
                    const price = p.tariff_info ? ` — ${p.tariff_info.hourly_rate} сом/ч` : '';
                    statusText += `  ${icon} ${p.name}${price}\n`;
                });
                statusText += '\n';
            }
            statusText += `━━━━━━━━━━━━━━\n✅ Свободно: *${freePlaces.length}* | 🔴 Занято: *${occupiedPlaces.length}*`;
            return bot.sendMessage(chatId, statusText, { parse_mode: 'Markdown', ...mainKeyboard() });
        } catch (e) {
            return bot.sendMessage(chatId, '❌ Не удалось загрузить статус.', mainKeyboard());
        }
    }

    if (text === '👤 Мой профиль') {
        const rankIcons = { 'Новичок': '🌱', 'Постоянный': '⭐', 'VIP': '👑', 'Легенда': '🔥' };
        const rankIcon = rankIcons[client.rank] || '🎮';
        
        let profText = `━━━ 👤 *ПРОФИЛЬ* ━━━\n\n` +
            `🏷 Имя: *${client.name}*\n` +
            `${rankIcon} Ранг: *${client.rank}*\n` +
            `💰 Бонусы: *${client.bonus_points}*\n` +
            `⏳ Сыграно часов: *${client.total_hours_played}*\n` +
            `👥 Рефералов: *${client.referrals_count || 0}*\n\n` +
            `_Чтобы получить QR код для кассы, нажми кнопку "Мой QR-код"._`;
        return bot.sendMessage(chatId, profText, { parse_mode: 'Markdown', ...mainKeyboard() });
    }

    if (text === '📅 Забронировать') {
        try {
            const places = await apiGet('/place_status/');
            const free = places.filter(p => p.status === 'free');

            if (free.length === 0) {
                return bot.sendMessage(chatId, '😔 Буквально все комнаты сейчас заняты.\nПопробуй позже!', mainKeyboard());
            }

            // Создаем клавиатуру с кнопками для каждой свободной комнаты
            const keyboardArray = free.map(p => [
                `📍 ${p.name} (${p.place_type || 'Std'}) — ${p.tariff_info ? p.tariff_info.hourly_rate + ' сом/ч' : ''} (ID: ${p.id})`
            ]);
            keyboardArray.push(['❌ Отмена']);

            userStates[chatId] = { step: 'BOOKING_PLACE' };
            
            return bot.sendMessage(chatId, '📅 *Выбери свободную комнату:*', {
                parse_mode: 'Markdown',
                reply_markup: { keyboard: keyboardArray, resize_keyboard: true }
            });
        } catch (e) {
            return bot.sendMessage(chatId, '❌ Ошибка при загрузке комнат.', mainKeyboard());
        }
    }

    if (text === '📋 Мои брони') {
        try {
            const bookings = await apiGet(`/my_bookings/${chatId}/`);
            const active = bookings.filter(b => ['pending', 'confirmed'].includes(b.status));

            if (active.length === 0) {
                return bot.sendMessage(chatId, '📋 У тебя нет активных бронирований.', mainKeyboard());
            }

            let bText = '📋 *Твои активные брони:*\n\n';
            const bKeyboard = [];
            
            active.forEach((b, i) => {
                const date = new Date(b.start_time).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
                const statusIcon = b.status === 'confirmed' ? '✅' : '⏳';
                const statusText = b.status === 'confirmed' ? 'Подтверждено' : 'Ожидает';
                bText += `${i + 1}. 📍 *${b.place_name}*\n   ⏰ ${date}\n   ${statusIcon} _${statusText}_\n\n`;
                
                bKeyboard.push([`🗑 Отменить бронь ${b.place_name} (ID: ${b.id})`]);
            });
            bKeyboard.push(['❌ Отмена']);

            return bot.sendMessage(chatId, bText + "\nЧтобы отменить, выбери кнопку внизу:", {
                parse_mode: 'Markdown',
                reply_markup: { keyboard: bKeyboard, resize_keyboard: true }
            });
        } catch (e) {
            return bot.sendMessage(chatId, '❌ Ошибка при загрузке бронирований.', mainKeyboard());
        }
    }

    if (text === '🎁 Рефералка') {
        try {
            let stats = await apiGet(`/referral_stats/${chatId}/`).catch(()=>({}));
            const count = stats.referrals_count || client.referrals_count || 0;
            const earned = count * 100;
            const botInfo = await bot.getMe();

            const rText = `━━━ 🎁 *РЕФЕРАЛЬНАЯ ПРОГРАММА* ━━━\n\n` +
                `*Как заработать бонусы?*\n` +
                `1️⃣ Кинь ссылку другу\n` +
                `2️⃣ Друг заходит и регистрируется\n` +
                `3️⃣ Вы ОБА получаете *100 сомов* на баланс!\n\n` +
                `🔑 Твой код: \`${client.referral_code || 'N/A'}\`\n\n` +
                `📊 *Твои успехи:*\n👥 Приглашено: *${count}*\n💰 Заработано: *${earned} бонусов*\n\n` +
                `Перешли другу вот это сообщение 👇:\n\`https://t.me/${botInfo.username}?start=${client.referral_code}\``;

            return bot.sendMessage(chatId, rText, { parse_mode: 'Markdown', ...mainKeyboard() });
        } catch(e) {}
    }

    if (text === '🆔 Мой QR-код') {
        try {
            const qrData = { type: 'cyberlounge_client', telegram_id: chatId, name: client.name, rank: client.rank };
            const qrBuffer = await generateQRBuffer(qrData);

            return bot.sendPhoto(chatId, qrBuffer, {
                caption: `🆔 *Твой QR-код*\n\nПокажи его на кассе администратору, чтобы быстро войти в сессию.\n\n👤 Имя: ${client.name}\n💎 Ранг: ${client.rank}`,
                parse_mode: 'Markdown',
                ...mainKeyboard()
            }, { filename: 'qr.png', contentType: 'image/png' });
        } catch (e) {
            return bot.sendMessage(chatId, '❌ Ошибка генерации QR.', mainKeyboard());
        }
    }
});
