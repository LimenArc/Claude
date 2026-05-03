-- GameConfig ModuleScript (ReplicatedStorage)
local GameConfig = {}

GameConfig.WORLD = {
	Size = 512,
	BiomeCount = 4,
	WaterLevel = 5,
	TreeDensity = 0.4,
	RockDensity = 0.2,
}

GameConfig.PLAYER = {
	BaseHealth = 100,
	BaseSpeed = 16,
	BaseDamage = 10,
	CoinStart = 50,
	RespawnTime = 5,
	InvincibleFrames = 0.5,
}

GameConfig.LOOT = {
	SpawnCount = 60,
	RespawnTime = 90,
	PickupRange = 8,
	Types = {
		{id = "coin_small",    display = "Small Coin Pouch", coinValue = 10,  rarity = 50},
		{id = "coin_medium",   display = "Coin Bag",         coinValue = 25,  rarity = 30},
		{id = "coin_large",    display = "Treasure Chest",   coinValue = 75,  rarity = 15},
		{id = "health_potion", display = "Health Potion",    healValue = 40,  rarity = 20},
		{id = "energy_crystal",display = "Energy Crystal",   energyBoost = 1, rarity = 10},
	},
}

GameConfig.SHOP = {
	Items = {
		-- Moves
		{id = "move_dash",      display = "Shadow Dash",      type = "move",   cost = 50,  desc = "Quickly dash forward"},
		{id = "move_spin",      display = "Spin Kick",        type = "move",   cost = 75,  desc = "360 spinning kick"},
		{id = "move_uppercut",  display = "Uppercut",         type = "move",   cost = 100, desc = "Launches enemy upward"},
		{id = "move_slam",      display = "Ground Slam",      type = "move",   cost = 150, desc = "Slam the ground dealing AoE damage"},
		{id = "move_teleport",  display = "Blink Strike",     type = "move",   cost = 200, desc = "Teleport behind and strike"},
		-- Weapons
		{id = "weapon_staff",       display = "Arcane Staff",      type = "weapon", cost = 150, damage = 35, desc = "Magical staff with range"},
		{id = "weapon_shuriken",    display = "Ninja Stars",       type = "weapon", cost = 100, damage = 20, desc = "Rapid thrown projectiles"},
		{id = "weapon_katana",      display = "Steel Katana",      type = "weapon", cost = 120, damage = 30, desc = "Fast melee sword"},
		{id = "weapon_greataxe",    display = "War Axe",           type = "weapon", cost = 180, damage = 50, desc = "Slow but heavy hits"},
		{id = "weapon_bow",         display = "Longbow",           type = "weapon", cost = 130, damage = 25, desc = "Precision ranged shots"},
	},
}

GameConfig.COMBAT = {
	PunchCooldown  = 0.4,
	BlockDuration  = 3,
	BlockReduction = 0.5,
	ComboWindow    = 1.2,
	MaxCombo       = 4,
	KnockbackForce = 40,
	HitboxSize     = Vector3.new(5, 5, 5),
}

GameConfig.LIGHTING = {
	Ambient         = Color3.fromRGB(80, 90, 110),
	OutdoorAmbient  = Color3.fromRGB(110, 120, 145),
	Brightness      = 2,
	ClockTime       = 14,
	FogEnd          = 800,
	FogColor        = Color3.fromRGB(180, 200, 220),
	ShadowSoftness  = 0.25,
}

GameConfig.MOD = {
	AdminIds = {}, -- add Roblox user IDs here
	Commands = {
		"give_coins", "set_health", "teleport", "speed",
		"god_mode", "spawn_loot", "clear_loot", "reset_player",
		"kick", "ban_temp", "fly",
	},
}

return GameConfig
