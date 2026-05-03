-- CombatClient LocalScript (StarterPlayerScripts)
local Players           = game:GetService("Players")
local UserInputService  = game:GetService("UserInputService")
local RunService        = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService      = game:GetService("TweenService")

local player    = Players.LocalPlayer
local Remotes   = ReplicatedStorage:WaitForChild("Remotes")
local PerformMove = Remotes:WaitForChild("PerformMove")
local BlockEvent  = Remotes:WaitForChild("BlockEvent")
local HitEffect   = Remotes:WaitForChild("HitEffect")
local EquipWeapon = Remotes:WaitForChild("EquipWeapon")

-- Player data (owned moves/weapons synced from server via UI)
local ownedMoves   = {"punch", "kick"}
local selectedMove = 1
local isBlocking   = false
local lastPunch    = 0
local comboCurrent = {}

-- Cooldown trackers (client-side visual only)
local moveCooldowns = {}
local MOVE_COOLDOWN = {
	punch          = 0.4, kick  = 0.6,
	move_dash      = 3,   move_spin    = 4,
	move_uppercut  = 5,   move_slam    = 8,
	move_teleport  = 7,
}

local function onCooldown(moveId)
	local last = moveCooldowns[moveId] or 0
	return tick() - last < (MOVE_COOLDOWN[moveId] or 1)
end
local function setCooldown(moveId)
	moveCooldowns[moveId] = tick()
end

-- Input bindings
-- Mouse1 = basic attack (cycles punch/kick)
-- Q = equipped special move 1
-- E = equipped special move 2
-- R = equipped special move 3
-- F = block
-- Z/X = cycle special move selection

local function doAttack(moveId)
	if onCooldown(moveId) then return end
	setCooldown(moveId)
	PerformMove:FireServer(moveId)
	-- Animate locally (optional: trigger animation on character)
	local char = player.Character
	if char then
		local hum    = char:FindFirstChild("Humanoid")
		local anim   = char:FindFirstChild("Animate")
	end
end

-- Basic attack on click
UserInputService.InputBegan:Connect(function(input, gpe)
	if gpe then return end
	local char = player.Character
	if not char then return end
	local hum = char:FindFirstChild("Humanoid")
	if not hum or hum.Health <= 0 then return end

	if input.UserInputType == Enum.UserInputType.MouseButton1 then
		-- Alternate punch/kick
		local t = tick()
		if t - lastPunch < 1.0 then
			doAttack("kick")
		else
			doAttack("punch")
		end
		lastPunch = t

	elseif input.KeyCode == Enum.KeyCode.Q then
		local move = ownedMoves[3]
		if move then doAttack(move) end

	elseif input.KeyCode == Enum.KeyCode.E then
		local move = ownedMoves[4]
		if move then doAttack(move) end

	elseif input.KeyCode == Enum.KeyCode.R then
		local move = ownedMoves[5]
		if move then doAttack(move) end

	elseif input.KeyCode == Enum.KeyCode.T then
		local move = ownedMoves[6]
		if move then doAttack(move) end

	elseif input.KeyCode == Enum.KeyCode.F then
		isBlocking = true
		BlockEvent:FireServer(true)

	elseif input.KeyCode == Enum.KeyCode.Z then
		selectedMove = math.max(1, selectedMove - 1)

	elseif input.KeyCode == Enum.KeyCode.X then
		selectedMove = math.min(#ownedMoves, selectedMove + 1)
	end
end)

UserInputService.InputEnded:Connect(function(input, gpe)
	if input.KeyCode == Enum.KeyCode.F and isBlocking then
		isBlocking = false
		BlockEvent:FireServer(false)
	end
end)

-- Receive new move unlock
Remotes:WaitForChild("UnlockMove").OnClientEvent:Connect(function(moveId)
	local found = false
	for _, m in ipairs(ownedMoves) do
		if m == moveId then found = true break end
	end
	if not found then
		table.insert(ownedMoves, moveId)
	end
end)

-- Hit effect particle burst
local function spawnHitEffect(pos, effectType)
	local part     = Instance.new("Part")
	part.Anchored  = true
	part.CanCollide = false
	part.Transparency = 1
	part.Size      = Vector3.new(0.1, 0.1, 0.1)
	part.Position  = pos
	part.Parent    = workspace

	local emit     = Instance.new("ParticleEmitter")
	if effectType == "aoe" then
		emit.Color     = ColorSequence.new(Color3.fromRGB(255, 120, 0))
		emit.Size      = NumberSequence.new({
			NumberSequenceKeypoint.new(0, 2), NumberSequenceKeypoint.new(1, 0)
		})
		emit.Speed     = NumberRange.new(20, 40)
		emit.Lifetime  = NumberRange.new(0.4, 0.7)
		emit.Rate      = 0
		emit.Parent    = part
		emit:Emit(40)
	elseif effectType == "teleport" then
		emit.Color     = ColorSequence.new(Color3.fromRGB(80, 0, 255))
		emit.Size      = NumberSequence.new({
			NumberSequenceKeypoint.new(0, 1.5), NumberSequenceKeypoint.new(1, 0)
		})
		emit.Speed     = NumberRange.new(15, 25)
		emit.Lifetime  = NumberRange.new(0.3, 0.5)
		emit.Rate      = 0
		emit.Parent    = part
		emit:Emit(25)
	else
		emit.Color     = ColorSequence.new(Color3.fromRGB(255, 255, 100))
		emit.Size      = NumberSequence.new({
			NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(1, 0)
		})
		emit.Speed     = NumberRange.new(10, 20)
		emit.Lifetime  = NumberRange.new(0.2, 0.4)
		emit.Rate      = 0
		emit.Parent    = part
		emit:Emit(15)
	end

	game:GetService("Debris"):AddItem(part, 1)
end

HitEffect.OnClientEvent:Connect(function(pos, effectType)
	spawnHitEffect(pos, effectType)
end)

-- Expose owned moves for UI
player:SetAttribute("OwnedMoves", table.concat(ownedMoves, ","))

RunService.Heartbeat:Connect(function()
	player:SetAttribute("OwnedMoves", table.concat(ownedMoves, ","))
	player:SetAttribute("IsBlocking", isBlocking)
end)
