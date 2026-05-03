-- MoveData ModuleScript (ReplicatedStorage)
local MoveData = {}

MoveData.Moves = {
	punch = {
		id = "punch", display = "Punch", damage = 10, cooldown = 0.4,
		range = 6, knockback = 20, animation = "rbxassetid://507766666",
		builtin = true,
	},
	kick = {
		id = "kick", display = "Kick", damage = 15, cooldown = 0.6,
		range = 7, knockback = 35, animation = "rbxassetid://507766388",
		builtin = true,
	},
	move_dash = {
		id = "move_dash", display = "Shadow Dash", damage = 0, cooldown = 3,
		range = 0, knockback = 10, duration = 0.3, speed = 80,
		animation = "rbxassetid://507767714",
	},
	move_spin = {
		id = "move_spin", display = "Spin Kick", damage = 22, cooldown = 4,
		range = 8, knockback = 50, aoe = true,
		animation = "rbxassetid://507766388",
	},
	move_uppercut = {
		id = "move_uppercut", display = "Uppercut", damage = 28, cooldown = 5,
		range = 6, knockback = 60, launchUp = 80,
		animation = "rbxassetid://507766666",
	},
	move_slam = {
		id = "move_slam", display = "Ground Slam", damage = 40, cooldown = 8,
		range = 12, knockback = 70, aoe = true, aoeRadius = 12,
		animation = "rbxassetid://507776514",
	},
	move_teleport = {
		id = "move_teleport", display = "Blink Strike", damage = 35, cooldown = 7,
		range = 20, knockback = 45,
		animation = "rbxassetid://507767714",
	},
}

MoveData.Combos = {
	{"punch", "punch", "kick"},
	{"punch", "kick", "punch"},
	{"kick", "kick", "move_slam"},
}

return MoveData
