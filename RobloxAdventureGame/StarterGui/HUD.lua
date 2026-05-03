-- HUD LocalScript (StarterGui)
local Players          = game:GetService("Players")
local TweenService     = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local player   = Players.LocalPlayer
local Remotes  = ReplicatedStorage:WaitForChild("Remotes")

-- ── Build HUD ────────────────────────────────────────────────────────────────
local screenGui       = Instance.new("ScreenGui")
screenGui.Name        = "HUD"
screenGui.ResetOnSpawn = false
screenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
screenGui.Parent      = player.PlayerGui

-- Corner helper
local function corner(parent, radius)
	local c    = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, radius or 8)
	c.Parent   = parent
end

local function stroke(parent, thickness, color)
	local s    = Instance.new("UIStroke")
	s.Thickness = thickness or 2
	s.Color     = color or Color3.fromRGB(0, 0, 0)
	s.Transparency = 0.4
	s.Parent    = parent
end

-- ── Health Bar ───────────────────────────────────────────────────────────────
local healthFrame   = Instance.new("Frame")
healthFrame.Name    = "HealthFrame"
healthFrame.Size    = UDim2.new(0, 260, 0, 30)
healthFrame.Position = UDim2.new(0, 20, 1, -80)
healthFrame.AnchorPoint = Vector2.new(0, 1)
healthFrame.BackgroundColor3 = Color3.fromRGB(30, 30, 30)
healthFrame.BorderSizePixel = 0
healthFrame.Parent  = screenGui
corner(healthFrame, 6)
stroke(healthFrame)

local healthBar     = Instance.new("Frame")
healthBar.Name      = "Bar"
healthBar.Size      = UDim2.new(1, 0, 1, 0)
healthBar.BackgroundColor3 = Color3.fromRGB(80, 220, 80)
healthBar.BorderSizePixel = 0
healthBar.Parent    = healthFrame
corner(healthBar, 6)

local healthLabel   = Instance.new("TextLabel")
healthLabel.Size    = UDim2.new(1, 0, 1, 0)
healthLabel.BackgroundTransparency = 1
healthLabel.Text    = "HP: 100 / 100"
healthLabel.TextColor3 = Color3.new(1, 1, 1)
healthLabel.Font    = Enum.Font.GothamBold
healthLabel.TextSize = 14
healthLabel.TextStrokeTransparency = 0.5
healthLabel.Parent  = healthFrame

-- HP icon label
local hpIcon        = Instance.new("TextLabel")
hpIcon.Size         = UDim2.new(0, 30, 0, 20)
hpIcon.Position     = UDim2.new(0, 0, -1, -2)
hpIcon.BackgroundTransparency = 1
hpIcon.Text         = "HP"
hpIcon.TextColor3   = Color3.fromRGB(100, 255, 100)
hpIcon.Font         = Enum.Font.GothamBold
hpIcon.TextSize     = 12
hpIcon.Parent       = healthFrame

-- ── Coin Display ─────────────────────────────────────────────────────────────
local coinFrame     = Instance.new("Frame")
coinFrame.Name      = "CoinFrame"
coinFrame.Size      = UDim2.new(0, 140, 0, 40)
coinFrame.Position  = UDim2.new(1, -160, 0, 20)
coinFrame.BackgroundColor3 = Color3.fromRGB(20, 20, 20)
coinFrame.BackgroundTransparency = 0.2
coinFrame.BorderSizePixel = 0
coinFrame.Parent    = screenGui
corner(coinFrame, 8)
stroke(coinFrame, 2, Color3.fromRGB(255, 200, 0))

local coinLabel     = Instance.new("TextLabel")
coinLabel.Name      = "CoinLabel"
coinLabel.Size      = UDim2.new(1, 0, 1, 0)
coinLabel.BackgroundTransparency = 1
coinLabel.Text      = "🪙 0"
coinLabel.TextColor3 = Color3.fromRGB(255, 220, 0)
coinLabel.Font       = Enum.Font.GothamBold
coinLabel.TextSize   = 20
coinLabel.Parent     = coinFrame

-- ── Kills Display ────────────────────────────────────────────────────────────
local killFrame     = Instance.new("Frame")
killFrame.Name      = "KillFrame"
killFrame.Size      = UDim2.new(0, 140, 0, 35)
killFrame.Position  = UDim2.new(1, -160, 0, 68)
killFrame.BackgroundColor3 = Color3.fromRGB(20, 20, 20)
killFrame.BackgroundTransparency = 0.2
killFrame.BorderSizePixel = 0
killFrame.Parent    = screenGui
corner(killFrame, 8)
stroke(killFrame, 2, Color3.fromRGB(255, 80, 80))

local killLabel     = Instance.new("TextLabel")
killLabel.Size      = UDim2.new(1, 0, 1, 0)
killLabel.BackgroundTransparency = 1
killLabel.Text      = "⚔ Kills: 0"
killLabel.TextColor3 = Color3.fromRGB(255, 100, 100)
killLabel.Font       = Enum.Font.GothamBold
killLabel.TextSize   = 16
killLabel.Parent     = killFrame

-- ── Move Hotbar ──────────────────────────────────────────────────────────────
local moveBar       = Instance.new("Frame")
moveBar.Name        = "MoveBar"
moveBar.Size        = UDim2.new(0, 400, 0, 70)
moveBar.Position    = UDim2.new(0.5, 0, 1, -90)
moveBar.AnchorPoint = Vector2.new(0.5, 1)
moveBar.BackgroundTransparency = 1
moveBar.Parent      = screenGui

local moveLayout    = Instance.new("UIListLayout")
moveLayout.FillDirection = Enum.FillDirection.Horizontal
moveLayout.HorizontalAlignment = Enum.HorizontalAlignment.Center
moveLayout.Padding  = UDim.new(0, 6)
moveLayout.Parent   = moveBar

local MOVE_KEYS    = {"M1", "M1", "Q", "E", "R", "T"}
local MOVE_NAMES   = {"Punch", "Kick", "Move3", "Move4", "Move5", "Move6"}
local moveSlots    = {}

for i = 1, 6 do
	local slot       = Instance.new("Frame")
	slot.Name        = "Slot" .. i
	slot.Size        = UDim2.new(0, 58, 0, 58)
	slot.BackgroundColor3 = Color3.fromRGB(25, 25, 35)
	slot.BackgroundTransparency = 0.15
	slot.BorderSizePixel = 0
	slot.Parent      = moveBar
	corner(slot, 8)
	stroke(slot, 2, Color3.fromRGB(80, 80, 120))

	local keyLabel   = Instance.new("TextLabel")
	keyLabel.Size    = UDim2.new(1, 0, 0, 18)
	keyLabel.Position = UDim2.new(0, 0, 0, 0)
	keyLabel.BackgroundTransparency = 1
	keyLabel.Text    = MOVE_KEYS[i]
	keyLabel.TextColor3 = Color3.fromRGB(180, 180, 180)
	keyLabel.Font    = Enum.Font.Gotham
	keyLabel.TextSize = 11
	keyLabel.Parent  = slot

	local nameLabel  = Instance.new("TextLabel")
	nameLabel.Size   = UDim2.new(1, 0, 1, -18)
	nameLabel.Position = UDim2.new(0, 0, 0, 18)
	nameLabel.BackgroundTransparency = 1
	nameLabel.Text   = MOVE_NAMES[i]
	nameLabel.TextColor3 = Color3.new(1, 1, 1)
	nameLabel.Font   = Enum.Font.GothamBold
	nameLabel.TextSize = 11
	nameLabel.TextWrapped = true
	nameLabel.Parent = slot

	local cooldownOverlay = Instance.new("Frame")
	cooldownOverlay.Name = "Cooldown"
	cooldownOverlay.Size = UDim2.new(1, 0, 0, 0)
	cooldownOverlay.Position = UDim2.new(0, 0, 1, 0)
	cooldownOverlay.AnchorPoint = Vector2.new(0, 1)
	cooldownOverlay.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
	cooldownOverlay.BackgroundTransparency = 0.3
	cooldownOverlay.BorderSizePixel = 0
	cooldownOverlay.Parent = slot
	corner(cooldownOverlay, 8)

	moveSlots[i] = {slot = slot, nameLabel = nameLabel, cooldown = cooldownOverlay}
end

-- ── Block indicator ──────────────────────────────────────────────────────────
local blockIndicator = Instance.new("TextLabel")
blockIndicator.Name  = "BlockIndicator"
blockIndicator.Size  = UDim2.new(0, 160, 0, 40)
blockIndicator.Position = UDim2.new(0.5, 0, 0.7, 0)
blockIndicator.AnchorPoint = Vector2.new(0.5, 0.5)
blockIndicator.BackgroundColor3 = Color3.fromRGB(30, 100, 200)
blockIndicator.BackgroundTransparency = 0.3
blockIndicator.BorderSizePixel = 0
blockIndicator.Text  = "🛡 BLOCKING"
blockIndicator.TextColor3 = Color3.new(1, 1, 1)
blockIndicator.Font  = Enum.Font.GothamBold
blockIndicator.TextSize = 18
blockIndicator.Visible = false
blockIndicator.Parent = screenGui
corner(blockIndicator, 10)

-- ── Notification system ──────────────────────────────────────────────────────
local notifContainer = Instance.new("Frame")
notifContainer.Name  = "Notifications"
notifContainer.Size  = UDim2.new(0, 300, 0, 300)
notifContainer.Position = UDim2.new(0.5, 0, 0, 20)
notifContainer.AnchorPoint = Vector2.new(0.5, 0)
notifContainer.BackgroundTransparency = 1
notifContainer.Parent = screenGui

local notifLayout    = Instance.new("UIListLayout")
notifLayout.FillDirection = Enum.FillDirection.Vertical
notifLayout.HorizontalAlignment = Enum.HorizontalAlignment.Center
notifLayout.Padding  = UDim.new(0, 4)
notifLayout.SortOrder = Enum.SortOrder.LayoutOrder
notifLayout.Parent   = notifContainer

local notifQueue     = 0

local function showNotif(text, color)
	notifQueue += 1
	local frame       = Instance.new("Frame")
	frame.LayoutOrder = notifQueue
	frame.Size        = UDim2.new(1, 0, 0, 36)
	frame.BackgroundColor3 = color or Color3.fromRGB(30, 30, 30)
	frame.BackgroundTransparency = 0.15
	frame.BorderSizePixel = 0
	frame.Parent      = notifContainer
	corner(frame, 8)
	stroke(frame, 2, color or Color3.fromRGB(80, 80, 80))

	local label       = Instance.new("TextLabel")
	label.Size        = UDim2.new(1, -16, 1, 0)
	label.Position    = UDim2.new(0, 8, 0, 0)
	label.BackgroundTransparency = 1
	label.Text        = text
	label.TextColor3  = Color3.new(1, 1, 1)
	label.Font        = Enum.Font.Gotham
	label.TextSize    = 14
	label.TextStrokeTransparency = 0.5
	label.Parent      = frame

	task.delay(3, function()
		TweenService:Create(frame, TweenInfo.new(0.4), {
			BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 0)
		}):Play()
		task.delay(0.4, function() frame:Destroy() end)
	end)
end

-- Expose globally
_G.ShowNotif = showNotif

-- ── Update functions ─────────────────────────────────────────────────────────
local function updateMoveBar()
	local movesStr = player:GetAttribute("OwnedMoves") or "punch,kick"
	local moves    = {}
	for m in movesStr:gmatch("[^,]+") do
		table.insert(moves, m)
	end

	local DISPLAY = {
		punch = "Punch", kick = "Kick",
		move_dash = "Dash", move_spin = "Spin",
		move_uppercut = "Uppercut", move_slam = "Slam",
		move_teleport = "Blink",
	}

	for i, slot in ipairs(moveSlots) do
		local moveId = moves[i]
		if moveId then
			slot.nameLabel.Text = DISPLAY[moveId] or moveId
			slot.slot.BackgroundColor3 = Color3.fromRGB(35, 35, 55)
		else
			slot.nameLabel.Text = "--"
			slot.slot.BackgroundColor3 = Color3.fromRGB(20, 20, 25)
		end
	end
end

-- ── Remote listeners ─────────────────────────────────────────────────────────
Remotes:WaitForChild("UpdateHealth").OnClientEvent:Connect(function(hp, maxHp)
	local ratio = math.clamp(hp / maxHp, 0, 1)
	TweenService:Create(healthBar, TweenInfo.new(0.2), {
		Size = UDim2.new(ratio, 0, 1, 0)
	}):Play()
	local hpColor
	if ratio > 0.6 then
		hpColor = Color3.fromRGB(80, 220, 80)
	elseif ratio > 0.3 then
		hpColor = Color3.fromRGB(220, 180, 0)
	else
		hpColor = Color3.fromRGB(220, 60, 60)
	end
	healthBar.BackgroundColor3 = hpColor
	healthLabel.Text = "HP: " .. math.floor(hp) .. " / " .. math.floor(maxHp)
end)

Remotes:WaitForChild("UpdateCoins").OnClientEvent:Connect(function(coins)
	coinLabel.Text = "🪙 " .. tostring(coins)
	TweenService:Create(coinFrame, TweenInfo.new(0.1), {
		Size = UDim2.new(0, 155, 0, 44)
	}):Play()
	task.delay(0.12, function()
		TweenService:Create(coinFrame, TweenInfo.new(0.1), {
			Size = UDim2.new(0, 140, 0, 40)
		}):Play()
	end)
end)

Remotes:WaitForChild("UnlockMove").OnClientEvent:Connect(function(moveId)
	showNotif("Unlocked move: " .. moveId, Color3.fromRGB(0, 140, 255))
	updateMoveBar()
end)

Remotes:WaitForChild("UnlockWeapon").OnClientEvent:Connect(function(weaponId)
	showNotif("Unlocked weapon: " .. weaponId, Color3.fromRGB(255, 140, 0))
end)

-- Block indicator
game:GetService("RunService").Heartbeat:Connect(function()
	local blocking = player:GetAttribute("IsBlocking")
	blockIndicator.Visible = blocking == true
	updateMoveBar()
end)

-- Leaderstats kill tracking
task.spawn(function()
	while true do
		task.wait(2)
		local ls = player:FindFirstChild("leaderstats")
		if ls then
			local k = ls:FindFirstChild("Kills")
			if k then killLabel.Text = "⚔ Kills: " .. k.Value end
		end
	end
end)

-- Loot pickup feedback
Remotes:WaitForChild("PickupLoot").OnClientEvent:Connect(function(_, lootType, value)
	local LOOT_DISPLAY = {
		coin_small     = "+ " .. value .. " coins",
		coin_medium    = "+ " .. value .. " coins",
		coin_large     = "+ " .. value .. " coins (chest!)",
		health_potion  = "Healed +" .. value .. " HP",
		energy_crystal = "Energy boosted!",
	}
	local col = lootType:find("coin") and Color3.fromRGB(255, 200, 0)
	         or lootType == "health_potion" and Color3.fromRGB(80, 200, 80)
	         or Color3.fromRGB(100, 180, 255)
	showNotif(LOOT_DISPLAY[lootType] or "Picked up item", col)
end)

showNotif("Welcome to Adventure World!", Color3.fromRGB(0, 180, 255))
updateMoveBar()
