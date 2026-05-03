-- LootSystem ModuleScript-style Script (ServerScriptService)
local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace         = game:GetService("Workspace")
local Debris            = game:GetService("Debris")
local GameConfig        = require(ReplicatedStorage:WaitForChild("GameConfig"))

local Remotes    = ReplicatedStorage:WaitForChild("Remotes")
local PickupLoot = Remotes:WaitForChild("PickupLoot")

local LootSystem = {}

local lootFolder = Instance.new("Folder")
lootFolder.Name   = "LootItems"
lootFolder.Parent = Workspace

local activeLoot  = {}  -- lootId -> {part, data, claimed}
local lootIdCount = 0

-- Colors per loot type
local LOOT_COLORS = {
	coin_small     = BrickColor.new("Bright yellow"),
	coin_medium    = BrickColor.new("Gold"),
	coin_large     = BrickColor.new("Bright orange"),
	health_potion  = BrickColor.new("Bright red"),
	energy_crystal = BrickColor.new("Bright blue"),
}

-- Rarity weighted pick
local function pickLootType()
	local types  = GameConfig.LOOT.Types
	local total  = 0
	for _, t in ipairs(types) do total += t.rarity end
	local roll   = math.random() * total
	local acc    = 0
	for _, t in ipairs(types) do
		acc += t.rarity
		if roll <= acc then return t end
	end
	return types[1]
end

-- Create glowing loot part
local function createLootPart(position, lootData)
	lootIdCount += 1
	local id = lootIdCount

	local part         = Instance.new("Part")
	part.Name          = "Loot_" .. id
	part.Anchored      = true
	part.CanCollide    = false
	part.Size          = Vector3.new(1.5, 1.5, 1.5)
	part.Shape         = lootData.id == "health_potion" and Enum.PartType.Ball or Enum.PartType.Block
	part.CFrame        = CFrame.new(position)
	part.BrickColor    = LOOT_COLORS[lootData.id] or BrickColor.new("Bright yellow")
	part.Material      = Enum.Material.Neon
	part.CastShadow    = false
	part.Parent        = lootFolder

	-- Label
	local billboard    = Instance.new("BillboardGui")
	billboard.Size     = UDim2.new(0, 120, 0, 40)
	billboard.StudsOffset = Vector3.new(0, 2.5, 0)
	billboard.AlwaysOnTop = false
	billboard.Parent   = part

	local label        = Instance.new("TextLabel")
	label.Size         = UDim2.new(1, 0, 1, 0)
	label.BackgroundTransparency = 1
	label.Text         = lootData.display
	label.TextColor3   = Color3.new(1, 1, 1)
	label.TextStrokeTransparency = 0
	label.Font         = Enum.Font.GothamBold
	label.TextScaled   = true
	label.Parent       = billboard

	-- Hover animation
	local startY     = position.Y
	local t          = 0
	local connection
	connection = game:GetService("RunService").Heartbeat:Connect(function(dt)
		t += dt
		if not part or not part.Parent then
			connection:Disconnect()
			return
		end
		part.CFrame = CFrame.new(position.X, startY + math.sin(t * 2) * 0.4, position.Z)
		           * CFrame.Angles(0, t, 0)
	end)

	activeLoot[id] = {part = part, data = lootData, claimed = false, connection = connection}
	return id, part
end

-- Raycast to find ground under a point
local function findGroundAt(x, z)
	local origin = Vector3.new(x, 300, z)
	local dir    = Vector3.new(0, -500, 0)
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Include
	params.FilterDescendantsInstances = {Workspace.Terrain, Workspace:FindFirstChild("Landmarks")}
	local result = Workspace:Raycast(origin, dir, params)
	if result then
		return result.Position + Vector3.new(0, 1.5, 0)
	end
	return nil
end

-- Public: spawn loot at specific position
function LootSystem.SpawnLootAt(position)
	local lootData = pickLootType()
	return createLootPart(position + Vector3.new(0, 2, 0), lootData)
end

-- Spawn initial loot around map
local function initialSpawn()
	local count    = GameConfig.LOOT.SpawnCount
	local halfSize = GameConfig.WORLD.Size / 2 - 20
	math.randomseed(99999)

	-- Prefer hidden spots: under trees, near rocks, behind hills
	local spawnedCount = 0
	local attempts     = 0

	while spawnedCount < count and attempts < count * 8 do
		attempts += 1
		local x   = math.random(-halfSize, halfSize)
		local z   = math.random(-halfSize, halfSize)
		local pos = findGroundAt(x, z)
		if pos and pos.Y > GameConfig.WORLD.WaterLevel + 2 then
			-- Slightly off-path (not in open centre)
			local distFromCentre = math.sqrt(x * x + z * z)
			if distFromCentre > 30 then
				createLootPart(pos, pickLootType())
				spawnedCount += 1
			end
		end
	end
	print("[LootSystem] Spawned", spawnedCount, "loot items")
end

-- Pickup proximity check (server validates)
game:GetService("RunService").Heartbeat:Connect(function()
	local pickupRange = GameConfig.LOOT.PickupRange
	for id, entry in pairs(activeLoot) do
		if not entry.claimed and entry.part and entry.part.Parent then
			local lootPos = entry.part.Position
			for _, player in ipairs(Players:GetPlayers()) do
				if player.Character then
					local hrp = player.Character:FindFirstChild("HumanoidRootPart")
					if hrp and (hrp.Position - lootPos).Magnitude <= pickupRange then
						entry.claimed = true
						if entry.connection then entry.connection:Disconnect() end

						local data = entry.data
						PickupLoot:FireClient(player, id, data.id,
							data.coinValue or data.healValue or data.energyBoost or 0)

						-- Notify server to apply effect (re-fire from client triggers server handler)
						local pdata = game.ReplicatedStorage:WaitForChild("Remotes")
						              :FindFirstChild("PickupLoot")
						-- Handle via the existing PickupLoot server handler
						local hum = player.Character:FindFirstChild("Humanoid")
						if data.id == "health_potion" and hum then
							hum.Health = math.min(hum.Health + (data.healValue or 0), hum.MaxHealth)
						end

						-- Actually update coins on server
						local pm = require(game.ServerScriptService:FindFirstChild("PlayerManager") or
						           game.ServerScriptService:FindFirstChild("PlayerData"))
						-- We'll fire back to the existing remote which triggers PlayerManager
						-- Note: since PlayerManager owns BuyItem/PickupLoot events,
						-- we apply coins here directly via a brief coupling:
						-- Instead emit back: (server-to-server requires module access)
						-- For simplicity, apply coin update here
						if data.coinValue then
							local ls = player:FindFirstChild("leaderstats")
							if ls then
								local c = ls:FindFirstChild("Coins")
								if c then c.Value += data.coinValue end
							end
							local r = ReplicatedStorage.Remotes:FindFirstChild("UpdateCoins")
							if r then
								local coins = (ls and ls.Coins and ls.Coins.Value) or 0
								r:FireClient(player, coins)
							end
						end

						-- Remove part after brief sparkle effect
						entry.part.Material = Enum.Material.SmoothPlastic
						entry.part.Size     = Vector3.new(0.1, 0.1, 0.1)
						Debris:AddItem(entry.part, 0.2)
						activeLoot[id] = nil
						break
					end
				end
			end
		end
	end
end)

-- Periodic respawn
task.spawn(function()
	while true do
		task.wait(GameConfig.LOOT.RespawnTime)
		-- Spawn a few replacements
		local halfSize = GameConfig.WORLD.Size / 2 - 20
		for _ = 1, 5 do
			local x   = math.random(-halfSize, halfSize)
			local z   = math.random(-halfSize, halfSize)
			local pos = findGroundAt(x, z)
			if pos and pos.Y > GameConfig.WORLD.WaterLevel + 2 then
				createLootPart(pos, pickLootType())
			end
		end
	end
end)

-- Start
task.delay(3, initialSpawn) -- wait for world to build

print("[LootSystem] Ready")
