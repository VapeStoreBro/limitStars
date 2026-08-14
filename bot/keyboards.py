from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="⭐ Купить Stars", callback_data="buy:start")],
        [InlineKeyboardButton(text="📦 Мои заказы", callback_data="orders:mine")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="🛠 Админка", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recipient_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Себе", callback_data="buy:recipient:self"),
            InlineKeyboardButton(text="🎁 Другу", callback_data="buy:recipient:friend"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="buy:cancel")],
    ])


def amount_menu() -> InlineKeyboardMarkup:
    values = (50, 100, 250, 500, 1000, 2500, 5000, 10000)
    rows = []
    for i in range(0, len(values), 2):
        rows.append([
            InlineKeyboardButton(text=f"{values[i]} ⭐", callback_data=f"buy:amount:{values[i]}"),
            InlineKeyboardButton(text=f"{values[i+1]} ⭐", callback_data=f"buy:amount:{values[i+1]}"),
        ])
    rows.append([InlineKeyboardButton(text="✏️ Своё количество", callback_data="buy:amount:custom")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="buy:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", callback_data="buy:confirm")],
        [InlineKeyboardButton(text="⬅️ Изменить количество", callback_data="buy:back_amount")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="buy:cancel")],
    ])


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
        [
            InlineKeyboardButton(text="💰 Цена продажи", callback_data="admin:sale_price"),
            InlineKeyboardButton(text="🧾 Закуп", callback_data="admin:cost_price"),
        ],
        [InlineKeyboardButton(text="👥 Особые цены", callback_data="admin:special")],
        [InlineKeyboardButton(text="📦 Последние заказы", callback_data="admin:orders")],
        [InlineKeyboardButton(text="⚙️ Статус системы", callback_data="admin:system")],
        [InlineKeyboardButton(text="⬅️ В магазин", callback_data="menu:home")],
    ])


def special_mode_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 По закупу", callback_data="admin:special_mode:cost")],
        [InlineKeyboardButton(text="💵 Фикс. цена/⭐", callback_data="admin:special_mode:fixed")],
        [InlineKeyboardButton(text="📈 Закуп + %", callback_data="admin:special_mode:cost_plus_percent")],
        [InlineKeyboardButton(text="❌ Удалить особую цену", callback_data="admin:special_mode:remove")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:home")],
    ])
