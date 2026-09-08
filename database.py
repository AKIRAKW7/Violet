import aiosqlite
import time

DB_NAME = "violet.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                balance INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                reputation INTEGER DEFAULT 0,
                last_daily INTEGER DEFAULT 0,
                last_work INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        # Actualizar bases de datos antiguas
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in await cursor.fetchall()}

        if "last_daily" not in columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN last_daily INTEGER DEFAULT 0"
            )

        if "last_work" not in columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN last_work INTEGER DEFAULT 0"
            )

        if "luck" not in columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN luck INTEGER DEFAULT 0"
            )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                species TEXT NOT NULL,
                hunger INTEGER DEFAULT 100,
                happiness INTEGER DEFAULT 100,
                energy INTEGER DEFAULT 100,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                partner_id INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id, item)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS social_achievements (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                achievement TEXT NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id, achievement)
            )
        """)


        await db.execute("""
            CREATE TABLE IF NOT EXISTS mining_stats (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                tool_level INTEGER DEFAULT 1,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS mining_inventory (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, item)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS fishing_stats (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                rod_level INTEGER DEFAULT 1,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS fish_inventory (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, item)
            )
        """)

    
        await db.execute("""
            CREATE TABLE IF NOT EXISTS activity_missions (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                mission_id TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                claimed INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, mission_id)
            )
        """)
    
        await db.commit()


async def get_user(user_id, guild_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT user_id, guild_id, balance, xp, level, reputation
            FROM users
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))

        user = await cursor.fetchone()

        if user is None:

            await db.execute("""
                INSERT INTO users
                (user_id, guild_id, balance, xp, level, reputation,
                 last_daily, last_work)
                VALUES (?, ?, 0, 0, 1, 0, 0, 0)
            """, (user_id, guild_id))

            await db.commit()

            return (user_id, guild_id, 0, 0, 1, 0)

        return user


async def add_balance(user_id, guild_id, amount):

    await get_user(user_id, guild_id)

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ? AND guild_id = ?
        """, (amount, user_id, guild_id))

        await db.commit()


async def remove_balance(user_id, guild_id, amount):

    user = await get_user(user_id, guild_id)

    balance = user[2]

    if balance < amount:
        return False

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ? AND guild_id = ?
        """, (amount, user_id, guild_id))

        await db.commit()

    return True


async def claim_daily(user_id, guild_id):

    await get_user(user_id, guild_id)

    now = int(time.time())

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT last_daily
            FROM users
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))

        row = await cursor.fetchone()

        last_daily = row[0] if row else 0

        if now - last_daily < 86400:
            return False, 86400 - (now - last_daily)

        cursor = await db.execute(
            "SELECT luck FROM users WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        luck_row = await cursor.fetchone()
        luck = luck_row[0] if luck_row else 0

        reward = 500 + (luck * 125)

        await db.execute("""
            UPDATE users
            SET balance = balance + ?,
                last_daily = ?
            WHERE user_id = ? AND guild_id = ?
        """, (reward, now, user_id, guild_id))

        await db.commit()

    return True, reward


async def work(user_id, guild_id):

    await get_user(user_id, guild_id)

    now = int(time.time())

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT last_work
            FROM users
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))

        row = await cursor.fetchone()

        last_work = row[0] if row else 0

        if now - last_work < 3600:
            return False, 3600 - (now - last_work)

        cursor = await db.execute(
            "SELECT luck FROM users WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        luck_row = await cursor.fetchone()
        luck = luck_row[0] if luck_row else 0

        base_reward = 100 + (now % 401)
        reward = base_reward + (base_reward * luck // 4)

        await db.execute("""
            UPDATE users
            SET balance = balance + ?,
                last_work = ?
            WHERE user_id = ? AND guild_id = ?
        """, (reward, now, user_id, guild_id))

        await db.commit()

    return True, reward


async def add_reputation(user_id, guild_id, amount=1):

    await get_user(user_id, guild_id)

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            UPDATE users
            SET reputation = reputation + ?
            WHERE user_id = ? AND guild_id = ?
        """, (amount, user_id, guild_id))

        await db.commit()


async def add_xp(user_id, guild_id, amount):

    user = await get_user(user_id, guild_id)

    old_xp = user[3]
    old_level = user[4]

    new_xp = old_xp + amount
    new_level = (new_xp // 100) + 1

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            UPDATE users
            SET xp = ?, level = ?
            WHERE user_id = ? AND guild_id = ?
        """, (new_xp, new_level, user_id, guild_id))

        await db.commit()

    return new_xp, new_level, old_level


async def create_pet(user_id, guild_id, name, species):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT user_id
            FROM pets
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))

        if await cursor.fetchone():
            return False

        await db.execute("""
            INSERT INTO pets
            (user_id, guild_id, name, species,
             hunger, happiness, energy)
            VALUES (?, ?, ?, ?, 100, 100, 100)
        """, (user_id, guild_id, name, species))

        await db.commit()

    return True


async def get_pet(user_id, guild_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT name, species, hunger, happiness, energy
            FROM pets
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))

        return await cursor.fetchone()


async def update_pet(
    user_id,
    guild_id,
    hunger=0,
    happiness=0,
    energy=0
):

    pet = await get_pet(user_id, guild_id)

    if pet is None:
        return False

    new_hunger = max(0, min(100, pet[2] + hunger))
    new_happiness = max(0, min(100, pet[3] + happiness))
    new_energy = max(0, min(100, pet[4] + energy))

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            UPDATE pets
            SET hunger = ?,
                happiness = ?,
                energy = ?
            WHERE user_id = ? AND guild_id = ?
        """, (
            new_hunger,
            new_happiness,
            new_energy,
            user_id,
            guild_id
        ))

        await db.commit()

    return True


async def set_partner(user_id, guild_id, partner_id):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            INSERT INTO relationships
            (user_id, guild_id, partner_id)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, guild_id)
            DO UPDATE SET partner_id = excluded.partner_id
        """, (user_id, guild_id, partner_id))

        await db.commit()


async def get_partner(user_id, guild_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT partner_id
            FROM relationships
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))

        row = await cursor.fetchone()

        return row[0] if row else 0


async def add_item(user_id, guild_id, item, quantity=1):

    await get_user(user_id, guild_id)

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            INSERT INTO inventory
            (user_id, guild_id, item, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, guild_id, item)
            DO UPDATE SET quantity = quantity + excluded.quantity
        """, (user_id, guild_id, item, quantity))

        await db.commit()


async def remove_item(user_id, guild_id, item, quantity=1):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT quantity
            FROM inventory
            WHERE user_id = ? AND guild_id = ? AND item = ?
        """, (user_id, guild_id, item))

        row = await cursor.fetchone()

        if row is None or row[0] < quantity:
            return False

        await db.execute("""
            UPDATE inventory
            SET quantity = quantity - ?
            WHERE user_id = ? AND guild_id = ? AND item = ?
        """, (quantity, user_id, guild_id, item))

        await db.commit()

    return True


async def get_inventory(user_id, guild_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT item, quantity
            FROM inventory
            WHERE user_id = ? AND guild_id = ?
              AND quantity > 0
            ORDER BY item
        """, (user_id, guild_id))

        return await cursor.fetchall()
async def add_interaction(guild_id, user_id, target_id, action):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO interactions
            (guild_id, user_id, target_id, action, amount)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(guild_id, user_id, target_id, action)
            DO UPDATE SET amount = amount + 1
        """, (
            guild_id,
            user_id,
            target_id,
            action
        ))
        await db.commit()


async def get_interactions(guild_id, user_id, target_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT action, amount
            FROM interactions
            WHERE guild_id = ?
              AND user_id = ?
              AND target_id = ?
        """, (
            guild_id,
            user_id,
            target_id
        ))
        return await cursor.fetchall()


async def get_interaction_ranking(guild_id, limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT user_id, target_id, SUM(amount) AS total
            FROM interactions
            WHERE guild_id = ?
            GROUP BY user_id, target_id
            ORDER BY total DESC
            LIMIT ?
        """, (
            guild_id,
            limit
        ))
        return await cursor.fetchall()


async def add_warning(
    user_id,
    guild_id,
    moderator_id,
    reason
):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            INSERT INTO warnings
            (user_id, guild_id, moderator_id, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            guild_id,
            moderator_id,
            reason,
            int(time.time())
        ))

        await db.commit()


async def get_warnings(user_id, guild_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT reason, moderator_id, created_at
            FROM warnings
            WHERE user_id = ? AND guild_id = ?
            ORDER BY id DESC
        """, (user_id, guild_id))

        return await cursor.fetchall()


async def get_interaction_count(
    guild_id,
    user_id,
    target_id,
    action
):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT amount
            FROM interactions
            WHERE guild_id = ?
            AND user_id = ?
            AND target_id = ?
            AND action = ?
        """, (
            guild_id,
            user_id,
            target_id,
            action
        ))

        row = await cursor.fetchone()

        return row[0] if row else 0


async def get_total_interactions(
    guild_id,
    user_id,
    target_id
):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM interactions
            WHERE guild_id = ?
            AND user_id = ?
            AND target_id = ?
        """, (
            guild_id,
            user_id,
            target_id
        ))

        row = await cursor.fetchone()

        return row[0] if row else 0


# =========================================================
# LOGROS SOCIALES
# =========================================================

async def desbloquear_logro(guild_id, user_id, achievement):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            INSERT OR IGNORE INTO social_achievements
            (guild_id, user_id, achievement)
            VALUES (?, ?, ?)
        """, (guild_id, user_id, achievement))

        await db.commit()

        return cursor.rowcount > 0


async def tiene_logro(guild_id, user_id, achievement):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT 1
            FROM social_achievements
            WHERE guild_id = ?
              AND user_id = ?
              AND achievement = ?
        """, (guild_id, user_id, achievement))

        return await cursor.fetchone() is not None


async def get_logros_sociales(guild_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT achievement, unlocked_at
            FROM social_achievements
            WHERE guild_id = ?
              AND user_id = ?
            ORDER BY unlocked_at ASC
        """, (guild_id, user_id))

        return await cursor.fetchall()


# =========================================================
# MINERÍA
# =========================================================

async def get_mining_stats(guild_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT level, xp, tool_level
            FROM mining_stats
            WHERE guild_id = ? AND user_id = ?
        """, (guild_id, user_id))

        row = await cursor.fetchone()

        if row:
            return row

        await db.execute("""
            INSERT INTO mining_stats
            (guild_id, user_id, level, xp, tool_level)
            VALUES (?, ?, 1, 0, 1)
        """, (guild_id, user_id))

        await db.commit()

        return (1, 0, 1)


async def add_mining_xp(guild_id, user_id, amount):
    level, xp, tool_level = await get_mining_stats(
        guild_id,
        user_id
    )

    xp += amount

    while xp >= level * 100:
        xp -= level * 100
        level += 1

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE mining_stats
            SET level = ?, xp = ?
            WHERE guild_id = ? AND user_id = ?
        """, (
            level,
            xp,
            guild_id,
            user_id
        ))

        await db.commit()

    return level, xp, tool_level


async def set_mining_tool_level(guild_id, user_id, level):
    await get_mining_stats(guild_id, user_id)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE mining_stats
            SET tool_level = ?
            WHERE guild_id = ? AND user_id = ?
        """, (
            level,
            guild_id,
            user_id
        ))

        await db.commit()


async def add_mining_item(guild_id, user_id, item, quantity=1):
    await get_mining_stats(guild_id, user_id)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO mining_inventory
            (guild_id, user_id, item, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id, item)
            DO UPDATE SET quantity = quantity + excluded.quantity
        """, (
            guild_id,
            user_id,
            item,
            quantity
        ))

        await db.commit()


async def remove_mining_item(guild_id, user_id, item, quantity):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT quantity
            FROM mining_inventory
            WHERE guild_id = ?
              AND user_id = ?
              AND item = ?
        """, (
            guild_id,
            user_id,
            item
        ))

        row = await cursor.fetchone()

        if not row or row[0] < quantity:
            return False

        await db.execute("""
            UPDATE mining_inventory
            SET quantity = quantity - ?
            WHERE guild_id = ?
              AND user_id = ?
              AND item = ?
        """, (
            quantity,
            guild_id,
            user_id,
            item
        ))

        await db.commit()

        return True


async def get_mining_inventory(guild_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT item, quantity
            FROM mining_inventory
            WHERE guild_id = ?
              AND user_id = ?
              AND quantity > 0
            ORDER BY quantity DESC
        """, (
            guild_id,
            user_id
        ))

        return await cursor.fetchall()


# =========================================================
# PESCA
# =========================================================

async def get_fishing_stats(guild_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT level, xp, rod_level
            FROM fishing_stats
            WHERE guild_id = ? AND user_id = ?
        """, (guild_id, user_id))

        row = await cursor.fetchone()

        if row:
            return row

        await db.execute("""
            INSERT INTO fishing_stats
            (guild_id, user_id, level, xp, rod_level)
            VALUES (?, ?, 1, 0, 1)
        """, (guild_id, user_id))

        await db.commit()

        return (1, 0, 1)


async def add_fishing_xp(guild_id, user_id, amount):
    level, xp, rod_level = await get_fishing_stats(
        guild_id,
        user_id
    )

    xp += amount

    while xp >= level * 100:
        xp -= level * 100
        level += 1

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE fishing_stats
            SET level = ?, xp = ?
            WHERE guild_id = ? AND user_id = ?
        """, (
            level,
            xp,
            guild_id,
            user_id
        ))

        await db.commit()

    return level, xp, rod_level


async def set_fishing_rod_level(guild_id, user_id, level):
    await get_fishing_stats(guild_id, user_id)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE fishing_stats
            SET rod_level = ?
            WHERE guild_id = ? AND user_id = ?
        """, (
            level,
            guild_id,
            user_id
        ))

        await db.commit()


async def add_fish(guild_id, user_id, fish, quantity=1):
    await get_fishing_stats(guild_id, user_id)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO fish_inventory
            (guild_id, user_id, item, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id, item)
            DO UPDATE SET quantity = quantity + excluded.quantity
        """, (
            guild_id,
            user_id,
            fish,
            quantity
        ))

        await db.commit()


async def remove_fish(guild_id, user_id, fish, quantity):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT quantity
            FROM fish_inventory
            WHERE guild_id = ?
              AND user_id = ?
              AND item = ?
        """, (
            guild_id,
            user_id,
            fish
        ))

        row = await cursor.fetchone()

        if not row or row[0] < quantity:
            return False

        await db.execute("""
            UPDATE fish_inventory
            SET quantity = quantity - ?
            WHERE guild_id = ?
              AND user_id = ?
              AND item = ?
        """, (
            quantity,
            guild_id,
            user_id,
            fish
        ))

        await db.commit()

        return True


async def get_fish_inventory(guild_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT item, quantity
            FROM fish_inventory
            WHERE guild_id = ?
              AND user_id = ?
              AND quantity > 0
            ORDER BY quantity DESC
        """, (
            guild_id,
            user_id
        ))

        return await cursor.fetchall()


# =========================================================
# FUNCIONES - MISIONES DE MINERÍA Y PESCA
# =========================================================

async def get_mission(guild_id, user_id, mission_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT progress, completed
            FROM activity_missions
            WHERE guild_id = ?
              AND user_id = ?
              AND mission_id = ?
        """, (guild_id, user_id, mission_id))

        row = await cursor.fetchone()

        if row:
            return row

        await db.execute("""
            INSERT INTO activity_missions
            (guild_id, user_id, mission_id, progress, completed)
            VALUES (?, ?, ?, 0, 0)
        """, (guild_id, user_id, mission_id))

        await db.commit()

        return (0, 0)


async def add_mission_progress(
    guild_id,
    user_id,
    mission_id,
    amount=1,
    required=1
):
    progress, completed = await get_mission(
        guild_id,
        user_id,
        mission_id
    )

    if completed:
        return progress, True

    progress += amount

    if progress >= required:
        progress = required
        completed = 1

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE activity_missions
            SET progress = ?, completed = ?
            WHERE guild_id = ?
              AND user_id = ?
              AND mission_id = ?
        """, (
            progress,
            completed,
            guild_id,
            user_id,
            mission_id
        ))

        await db.commit()

    return progress, bool(completed)


async def get_missions(guild_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT mission_id, progress, completed
            FROM activity_missions
            WHERE guild_id = ?
              AND user_id = ?
            ORDER BY mission_id
        """, (guild_id, user_id))

        return await cursor.fetchall()


async def reset_mission(guild_id, user_id, mission_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE activity_missions
            SET progress = 0,
                completed = 0
            WHERE guild_id = ?
              AND user_id = ?
              AND mission_id = ?
        """, (
            guild_id,
            user_id,
            mission_id
        ))

        await db.commit()


async def claim_mission(guild_id, user_id, mission_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT progress, completed, claimed
            FROM activity_missions
            WHERE guild_id = ?
              AND user_id = ?
              AND mission_id = ?
        """, (guild_id, user_id, mission_id))

        row = await cursor.fetchone()

        if not row:
            return False, "not_found"

        progress, completed, claimed = row

        if not completed:
            return False, "not_completed"

        if claimed:
            return False, "already_claimed"

        await db.execute("""
            UPDATE activity_missions
            SET claimed = 1
            WHERE guild_id = ?
              AND user_id = ?
              AND mission_id = ?
        """, (guild_id, user_id, mission_id))

        await db.commit()

        return True, "claimed"


# =========================================================
# COLECCIONES
# =========================================================

async def add_collection_item(guild_id, user_id, category, item):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                item TEXT NOT NULL,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id, category, item)
            )
        """)

        await db.execute("""
            INSERT OR IGNORE INTO collections
            (guild_id, user_id, category, item)
            VALUES (?, ?, ?, ?)
        """, (guild_id, user_id, category, item))

        await db.commit()


async def get_collection(guild_id, user_id, category):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT item
            FROM collections
            WHERE guild_id = ?
              AND user_id = ?
              AND category = ?
            ORDER BY discovered_at ASC
        """, (guild_id, user_id, category))

        return await cursor.fetchall()


async def get_collection_count(guild_id, user_id, category):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT COUNT(*)
            FROM collections
            WHERE guild_id = ?
              AND user_id = ?
              AND category = ?
        """, (guild_id, user_id, category))

        resultado = await cursor.fetchone()
        return resultado[0] if resultado else 0

# =========================================================
# 🎰 ESTADÍSTICAS DEL CASINO
# =========================================================

async def registrar_casino(
    guild_id,
    user_id,
    apuesta,
    ganancia=0,
    victoria=False
):
    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS casino_stats (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                partidas INTEGER DEFAULT 0,
                victorias INTEGER DEFAULT 0,
                derrotas INTEGER DEFAULT 0,
                apostado INTEGER DEFAULT 0,
                ganancias INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        await db.execute("""
            INSERT OR IGNORE INTO casino_stats
            (guild_id, user_id)
            VALUES (?, ?)
        """, (guild_id, user_id))

        if victoria:
            await db.execute("""
                UPDATE casino_stats
                SET partidas = partidas + 1,
                    victorias = victorias + 1,
                    apostado = apostado + ?,
                    ganancias = ganancias + ?
                WHERE guild_id = ? AND user_id = ?
            """, (
                apuesta,
                ganancia,
                guild_id,
                user_id
            ))
        else:
            await db.execute("""
                UPDATE casino_stats
                SET partidas = partidas + 1,
                    derrotas = derrotas + 1,
                    apostado = apostado + ?
                WHERE guild_id = ? AND user_id = ?
            """, (
                apuesta,
                guild_id,
                user_id
            ))

        await db.commit()


async def get_casino_ranking(guild_id, limite=10):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT user_id, partidas, victorias, derrotas,
                   apostado, ganancias
            FROM casino_stats
            WHERE guild_id = ?
            ORDER BY ganancias DESC
            LIMIT ?
        """, (guild_id, limite))

        return await cursor.fetchall()


async def get_casino_stats(guild_id, user_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT partidas, victorias, derrotas,
                   apostado, ganancias
            FROM casino_stats
            WHERE guild_id = ? AND user_id = ?
        """, (guild_id, user_id))

        resultado = await cursor.fetchone()

        if resultado is None:
            return (0, 0, 0, 0, 0)

        return resultado

