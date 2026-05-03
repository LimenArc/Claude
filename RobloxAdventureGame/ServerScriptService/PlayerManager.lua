-- PlayerManager Script (ServerScriptService)
local Players            = game:GetService("Players")
local ReplicatedStorage  = game:GetService("ReplicatedStorage")
local ServerStorage      = game:GetService("ServerStorage")
local GameConfig         = require(ReplicatedStorage:WaitForChild("GameConfig"))

-- Remote events
local Remotes = ReplicatedStorage:FindFirstChild("Remotes")
if not Remotes then
	Remotes        = Instance.new("Folder")
	Remotes.Name   = "Remotes"
	Remotes.Parent = ReplicatedStorage
end

local function getOrMakeRemote(name, class)
	local r = Remotes:FindFirstChild(name)
	if not r then
		r = Instance.new(class)
		r.Name   = name
		r.Parent = Remotes
	end
	return r
end

local UpdateCoins    = getOrMakeRemote("UpdateCoins",    "RemoteEvent")
local UpdateHealth   = getOrMakeRemote("UpdateHealth",   "RemoteEvent")
local UnlockMove     = getOrMakeRemote("UnlockMove",     "RemoteEvent")
local UnlockWeapon   = getOrMakeRemote("UnlockWeapon",   "RemoteEvent")
local BuyItem        = getOrMakeRemote("BuyItem",        "RemoteFunction")
local PickupLoot     = getOrMakeRemote("PickupLoot",     "RemoteEvent")
local ModCommand     = getOrMakeRemote("ModCommand",     "RemoteFunction")
local GetPlayerData  = getOrMakeRemote("GetPlayerData",  "RemoteFunction")

-- DataStore (leaderstats)
local playerData = {}

local function initPlayerData(player)
	playerData[player.UserId] = {
		coins      = GameConfig.PLAYER.CoinStart,
		health     = GameConfig.PLAYER.BaseHealth,
		moves      = {"punch", "kick"},
		weapons    = {},
		equippedWeapon = nil,
		kills      = 0,
		deaths     = 0,
		godMode    = false,
		flyMode    = false,
	}
end

local function getData(player)
	return playerData[player.UserId]
end

-- Leaderstats
local function setupLeaderstats(player)
	local ls          = Instance.new("Folder")
	ls.Name           = "leaderstats"
	ls.Parent         = player

	local coins       = Instance.new("IntValue")
	coins.Name        = "Coins"
	coins.Value       = GameConfig.PLAYER.CoinStart
	coins.Parent      = ls

	local kills       = Instance.new("IntValue")
	kills.Name        = "Kills"
	kills.Value       = 0
	kills.Parent      = ls
end

local function updateLeaderstats(player)
	local data = getData(player)
	if not data then return end
	local ls   = player:FindFirstChild("leaderstats")
	if not ls then return end
	local c    = ls:FindFirstChild("Coins")
	if c then c.Value = data.coins end
	local k    = ls:FindFirstChild("Kills")
	if k then k.Value = data.kills end
end

-- Character setup
local function setupCharacter(player, character)
	local humanoid = character:WaitForChild("Humanoid")
	humanoid.MaxHealth  = GameConfig.PLAYER.BaseHealth
	humanoid.Health     = GameConfig.PLAYER.BaseHealth
	humanoid.WalkSpeed  = GameConfig.PLAYER.BaseSpeed

	local data = getData(player)

	-- Restore god mode
	if data and data.godMode then
		humanoid.MaxHealth = math.huge
		humanoid.Health    = math.huge
	end

	-- Tag for damage tracking
	local tag      = Instance.new("StringValue")
	tag.Name       = "PlayerId"
	tag.Value      = tostring(player.UserId)
	tag.Parent     = character

	-- Handle death
	humanoid.Died:Connect(function()
		if data then
			data.deaths += 1

			-- Find killer via humanoid tag
			local killerTag = humanoid:FindFirstChild("KillerTag")
			if killerTag then
				local killer = Players:GetPlayerByUserId(tonumber(killerTag.Value))
				if killer then
					local kd = getData(killer)
					if kd then
						kd.kills += 1
						kd.coins += 15
						UpdateCoins:FireClient(killer, kd.coins)
						updateLeaderstats(killer)
					end
				end
			end
		end

		task.delay(GameConfig.PLAYER.RespawnTime, function()
			player:LoadCharacter()
		end)
	end)

	-- Sync health changes
	humanoid.HealthChanged:Connect(function(hp)
		UpdateHealth:FireClient(player, hp, humanoid.MaxHealth)
	end)
end

-- Buy item handler
BuyItem.OnServerInvoke = function(player, itemId)
	local data = getData(player)
	if not data then return false, "No data" end

	local cfg    = GameConfig.SHOP
	local item
	for _, v in ipairs(cfg.Items) do
		if v.id == itemId then item = v break end
	end
	if not item then return false, "Invalid item" end

	-- Already owned?
	if item.type == "move" then
		for _, m in ipairs(data.moves) do
			if m == itemId then return false, "Already owned" end
		end
	elseif item.type == "weapon" then
		for _, w in ipairs(data.weapons) do
			if w == itemId then return false, "Already owned" end
		end
	end

	if data.coins < item.cost then return false, "Not enough coins" end

	data.coins -= item.cost
	UpdateCoins:FireClient(player, data.coins)
	updateLeaderstats(player)

	if item.type == "move" then
		table.insert(data.moves, itemId)
		UnlockMove:FireClient(player, itemId)
	elseif item.type == "weapon" then
		table.insert(data.weapons, itemId)
		UnlockWeapon:FireClient(player, itemId)
	end

	return true, "Purchased: " .. item.display
end

-- Loot pickup handler
PickupLoot.OnServerEvent:Connect(function(player, lootId, lootType, value)
	local data = getData(player)
	if not data then return end

	if lootType == "coin_small" or lootType == "coin_medium" or lootType == "coin_large" then
		data.coins += value
		UpdateCoins:FireClient(player, data.coins)
		updateLeaderstats(player)
	elseif lootType == "health_potion" then
		local char = player.Character
		if char then
			local hum = char:FindFirstChild("Humanoid")
			if hum then
				hum.Health = math.min(hum.Health + value, hum.MaxHealth)
			end
		end
	end
end)

-- GetPlayerData handler
GetPlayerData.OnServerInvoke = function(player)
	return getData(player)
end

-- Mod command handler
ModCommand.OnServerInvoke = function(player, cmd, args)
	local cfg   = GameConfig.MOD
	local isAdmin = false
	for _, id in ipairs(cfg.AdminIds) do
		if id == player.UserId then isAdmin = true break end
	end
	-- Allow studio test
	if game:GetService("RunService"):IsStudio() then isAdmin = true end
	if not isAdmin then return false, "No permission" end

	local target = args.target and Players:FindFirstChild(args.target) or player
	local tdata  = getData(target)

	if cmd == "give_coins" then
		local amount = tonumber(args.amount) or 100
		tdata.coins += amount
		UpdateCoins:FireClient(target, tdata.coins)
		updateLeaderstats(target)
		return true, "Gave " .. amount .. " coins to " .. target.Name

	elseif cmd == "set_health" then
		local hp  = tonumber(args.amount) or 100
		local char = target.Character
		if char then
			local hum = char:FindFirstChild("Humanoid")
			if hum then hum.Health = hp end
		end
		return true, "Set health to " .. hp

	elseif cmd == "god_mode" then
		tdata.godMode = not tdata.godMode
		local char    = target.Character
		if char then
			local hum = char:FindFirstChild("Humanoid")
			if hum then
				hum.MaxHealth = tdata.godMode and math.huge or GameConfig.PLAYER.BaseHealth
				hum.Health    = hum.MaxHealth
			end
		end
		return true, "God mode: " .. tostring(tdata.godMode)

	elseif cmd == "speed" then
		local spd  = tonumber(args.amount) or 16
		local char = target.Character
		if char then
			local hum = char:FindFirstChild("Humanoid")
			if hum then hum.WalkSpeed = spd end
		end
		return true, "Speed set to " .. spd

	elseif cmd == "teleport" then
		local char = target.Character
		if char and char:FindFirstChild("HumanoidRootPart") then
			char.HumanoidRootPart.CFrame = CFrame.new(
				tonumber(args.x) or 0,
				tonumber(args.y) or 20,
				tonumber(args.z) or 0
			)
		end
		return true, "Teleported"

	elseif cmd == "spawn_loot" then
		local LootSystem = require(game.ServerScriptService:FindFirstChild("LootSystem"))
		LootSystem.SpawnLootAt(target.Character and
			target.Character.HumanoidRootPart.Position or Vector3.new(0,20,0))
		return true, "Spawned loot"

	elseif cmd == "kick" then
		target:Kick("Kicked by moderator")
		return true, "Kicked " .. target.Name

	elseif cmd == "reset_player" then
		target:LoadCharacter()
		return true, "Reset player"

	elseif cmd == "fly" then
		tdata.flyMode = not tdata.flyMode
		game.ReplicatedStorage.Remotes:FindFirstChild("ToggleFly") and
			game.ReplicatedStorage.Remotes.ToggleFly:FireClient(target, tdata.flyMode)
		return true, "Fly: " .. tostring(tdata.flyMode)
	end

	return false, "Unknown command"
end

-- Player added/removed
Players.PlayerAdded:Connect(function(player)
	initPlayerData(player)
	setupLeaderstats(player)

	player.CharacterAdded:Connect(function(character)
		setupCharacter(player, character)
		task.defer(function()
			local data = getData(player)
			if data then UpdateCoins:FireClient(player, data.coins) end
		end)
	end)
end)

Players.PlayerRemoving:Connect(function(player)
	playerData[player.UserId] = nil
end)

-- Handle existing players (Studio)
for _, player in ipairs(Players:GetPlayers()) do
	initPlayerData(player)
	setupLeaderstats(player)
	if player.Character then
		setupCharacter(player, player.Character)
	end
end

print("[PlayerManager] Ready")
