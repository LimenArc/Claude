-- CombatSystem Script (ServerScriptService)
local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local GameConfig        = require(ReplicatedStorage:WaitForChild("GameConfig"))
local MoveData          = require(ReplicatedStorage:WaitForChild("MoveData"))

local Remotes      = ReplicatedStorage:WaitForChild("Remotes")
local PerformMove  = Instance.new("RemoteEvent"); PerformMove.Name  = "PerformMove";  PerformMove.Parent  = Remotes
local EquipWeapon  = Instance.new("RemoteEvent"); EquipWeapon.Name  = "EquipWeapon";  EquipWeapon.Parent  = Remotes
local HitEffect    = Instance.new("RemoteEvent"); HitEffect.Name    = "HitEffect";    HitEffect.Parent    = Remotes
local BlockEvent   = Instance.new("RemoteEvent"); BlockEvent.Name   = "BlockEvent";   BlockEvent.Parent   = Remotes

-- Rate limiting
local moveCooldowns = {} -- [player.UserId][moveId] = tickTime

local function getCooldown(player, moveId)
	moveCooldowns[player.UserId] = moveCooldowns[player.UserId] or {}
	local last = moveCooldowns[player.UserId][moveId] or 0
	return tick() - last
end

local function setCooldown(player, moveId)
	moveCooldowns[player.UserId] = moveCooldowns[player.UserId] or {}
	moveCooldowns[player.UserId][moveId] = tick()
end

-- Block state
local blockState = {} -- [player.UserId] = true/false

-- Apply damage to character
local function applyDamage(attacker, victim, damage)
	if not victim or not victim.Parent then return end
	local humanoid = victim:FindFirstChild("Humanoid")
	if not humanoid or humanoid.Health <= 0 then return end

	-- Check block
	local victimPlayer = Players:GetPlayerFromCharacter(victim)
	if victimPlayer and blockState[victimPlayer.UserId] then
		damage = damage * (1 - GameConfig.COMBAT.BlockReduction)
	end

	-- God mode check
	local pdata = game.ReplicatedStorage:FindFirstChild("Remotes")
	-- Tag killer
	local tag = humanoid:FindFirstChild("KillerTag")
	if not tag then
		tag      = Instance.new("StringValue")
		tag.Name = "KillerTag"
		tag.Parent = humanoid
	end
	tag.Value = tostring(attacker.UserId)

	humanoid:TakeDamage(damage)
end

-- Hitbox detection
local function getHitsInRadius(origin, radius, excludeChar)
	local hits = {}
	local params = OverlapParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = {excludeChar}

	local parts = game.Workspace:GetPartBoundsInRadius(origin, radius, params)
	local seen  = {}
	for _, part in ipairs(parts) do
		local char = part.Parent
		if char and not seen[char] then
			local hum = char:FindFirstChild("Humanoid")
			if hum and hum.Health > 0 then
				seen[char] = true
				table.insert(hits, char)
			end
		end
	end
	return hits
end

-- Apply knockback
local function applyKnockback(character, direction, force, upForce)
	local hrp = character:FindFirstChild("HumanoidRootPart")
	if not hrp then return end
	local vel = hrp:FindFirstChild("AssemblyLinearVelocity") -- newer API
	local bodyVel = Instance.new("LinearVelocity")
	-- Fallback: use BodyVelocity
	local bv = Instance.new("BodyVelocity")
	bv.Velocity   = direction * force + Vector3.new(0, upForce or 0, 0)
	bv.MaxForce   = Vector3.new(1e5, 1e5, 1e5)
	bv.Parent     = hrp
	game:GetService("Debris"):AddItem(bv, 0.15)
end

-- Move execution
PerformMove.OnServerEvent:Connect(function(player, moveId)
	local char = player.Character
	if not char then return end
	local hrp  = char:FindFirstChild("HumanoidRootPart")
	local hum  = char:FindFirstChild("Humanoid")
	if not hrp or not hum or hum.Health <= 0 then return end

	local move = MoveData.Moves[moveId]
	if not move then return end

	-- Cooldown check
	if getCooldown(player, moveId) < move.cooldown then return end
	setCooldown(player, moveId)

	local cfg = GameConfig.COMBAT

	if moveId == "move_dash" then
		local lookDir = hrp.CFrame.LookVector
		local bv      = Instance.new("BodyVelocity")
		bv.Velocity  = lookDir * move.speed
		bv.MaxForce  = Vector3.new(1e5, 0, 1e5)
		bv.Parent    = hrp
		game:GetService("Debris"):AddItem(bv, move.duration)

	elseif moveId == "move_teleport" then
		-- Find nearest enemy
		local nearest, nearDist = nil, move.range
		for _, p in ipairs(Players:GetPlayers()) do
			if p ~= player and p.Character then
				local ep = p.Character:FindFirstChild("HumanoidRootPart")
				if ep then
					local d = (ep.Position - hrp.Position).Magnitude
					if d < nearDist then nearest = p.Character; nearDist = d end
				end
			end
		end
		if nearest then
			local ep  = nearest:FindFirstChild("HumanoidRootPart")
			local dir = (hrp.Position - ep.Position).Unit
			hrp.CFrame = CFrame.new(ep.Position + dir * 3.5)
			applyDamage(player, nearest, move.damage)
			HitEffect:FireAllClients(ep.Position, "teleport")
			applyKnockback(nearest, dir, move.knockback)
		end

	elseif move.aoe then
		-- AoE moves: slam, spin
		local radius = move.aoeRadius or move.range
		local hits   = getHitsInRadius(hrp.Position, radius, char)
		HitEffect:FireAllClients(hrp.Position, "aoe")
		for _, victim in ipairs(hits) do
			applyDamage(player, victim, move.damage)
			local dir = (victim.HumanoidRootPart.Position - hrp.Position).Unit
			applyKnockback(victim, dir, move.knockback, move.launchUp or 0)
		end

	else
		-- Directional hit (punch, kick, uppercut)
		local lookDir = hrp.CFrame.LookVector
		local origin  = hrp.Position + lookDir * 2
		local hits    = getHitsInRadius(origin, move.range or 6, char)
		for _, victim in ipairs(hits) do
			applyDamage(player, victim, move.damage)
			applyKnockback(victim, lookDir, move.knockback, move.launchUp or 0)
			HitEffect:FireAllClients(victim.HumanoidRootPart.Position, "hit")
		end
	end
end)

-- Block handler
BlockEvent.OnServerEvent:Connect(function(player, blocking)
	blockState[player.UserId] = blocking
end)

-- Equip weapon (visual + stat tracking; actual projectiles handled client-side)
EquipWeapon.OnServerEvent:Connect(function(player, weaponId)
	-- Unequip previous tool
	local char = player.Character
	if not char then return end
	local backpack = player:FindFirstChild("Backpack")

	for _, tool in ipairs(char:GetChildren()) do
		if tool:IsA("Tool") then
			tool.Parent = backpack
		end
	end

	if weaponId == "unequip" then return end

	-- Find or create tool in backpack
	local tool = backpack and backpack:FindFirstChild(weaponId)
	if tool then
		tool.Parent = char
	end
end)

-- Clean up on leave
Players.PlayerRemoving:Connect(function(player)
	moveCooldowns[player.UserId] = nil
	blockState[player.UserId]    = nil
end)

print("[CombatSystem] Ready")
