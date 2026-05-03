-- ModMenu LocalScript (StarterGui)
local Players           = game:GetService("Players")
local TweenService      = game:GetService("TweenService")
local UserInputService  = game:GetService("UserInputService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local player   = Players.LocalPlayer
local Remotes  = ReplicatedStorage:WaitForChild("Remotes")
local ModCommand = Remotes:WaitForChild("ModCommand")

local screen   = Instance.new("ScreenGui")
screen.Name    = "ModMenu"
screen.ResetOnSpawn = false
screen.Enabled = false
screen.Parent  = player.PlayerGui

-- ── Helpers ───────────────────────────────────────────────────────────────────
local function corner(p, r)
	local c = Instance.new("UICorner"); c.CornerRadius = UDim.new(0, r or 8); c.Parent = p
end
local function stroke(p, t, col)
	local s = Instance.new("UIStroke"); s.Thickness = t or 2
	s.Color = col or Color3.fromRGB(100, 80, 160); s.Parent = p
end

local function newLabel(parent, text, textSize, color, font)
	local l = Instance.new("TextLabel")
	l.Size  = UDim2.new(1, 0, 0, 24)
	l.BackgroundTransparency = 1
	l.Text  = text
	l.TextColor3 = color or Color3.new(1, 1, 1)
	l.Font  = font or Enum.Font.GothamBold
	l.TextSize = textSize or 14
	l.TextXAlignment = Enum.TextXAlignment.Left
	l.Parent = parent
	return l
end

local function newButton(parent, text, color)
	local b = Instance.new("TextButton")
	b.Size  = UDim2.new(1, 0, 0, 34)
	b.BackgroundColor3 = color or Color3.fromRGB(60, 50, 100)
	b.BorderSizePixel = 0
	b.Text  = text
	b.TextColor3 = Color3.new(1, 1, 1)
	b.Font  = Enum.Font.GothamBold
	b.TextSize = 14
	b.Parent = parent
	corner(b, 8)
	return b
end

local function newInput(parent, placeholder)
	local f = Instance.new("Frame")
	f.Size  = UDim2.new(1, 0, 0, 32)
	f.BackgroundColor3 = Color3.fromRGB(20, 18, 32)
	f.BorderSizePixel = 0
	f.Parent = parent
	corner(f, 6)
	stroke(f, 1, Color3.fromRGB(80, 70, 120))

	local tb = Instance.new("TextBox")
	tb.Size  = UDim2.new(1, -12, 1, 0)
	tb.Position = UDim2.new(0, 6, 0, 0)
	tb.BackgroundTransparency = 1
	tb.PlaceholderText = placeholder or ""
	tb.PlaceholderColor3 = Color3.fromRGB(120, 110, 140)
	tb.Text = ""
	tb.TextColor3 = Color3.new(1, 1, 1)
	tb.Font = Enum.Font.Gotham
	tb.TextSize = 13
	tb.ClearTextOnFocus = false
	tb.Parent = f
	return tb, f
end

-- ── Main window ───────────────────────────────────────────────────────────────
local main     = Instance.new("Frame")
main.Name      = "ModMenuWindow"
main.Size      = UDim2.new(0, 460, 0, 560)
main.Position  = UDim2.new(0, 20, 0.5, 0)
main.AnchorPoint = Vector2.new(0, 0.5)
main.BackgroundColor3 = Color3.fromRGB(10, 8, 18)
main.BorderSizePixel = 0
main.Parent    = screen
corner(main, 14)
stroke(main, 2, Color3.fromRGB(120, 80, 200))

-- Drag support
local dragging, dragStart, startPos
main.InputBegan:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.MouseButton1 then
		dragging  = true
		dragStart = input.Position
		startPos  = main.Position
	end
end)
main.InputEnded:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.MouseButton1 then
		dragging = false
	end
end)
UserInputService.InputChanged:Connect(function(input)
	if dragging and input.UserInputType == Enum.UserInputType.MouseMovement then
		local delta = input.Position - dragStart
		main.Position = UDim2.new(
			startPos.X.Scale, startPos.X.Offset + delta.X,
			startPos.Y.Scale, startPos.Y.Offset + delta.Y
		)
	end
end)

-- Title
local titleBar = Instance.new("Frame")
titleBar.Size  = UDim2.new(1, 0, 0, 44)
titleBar.BackgroundColor3 = Color3.fromRGB(20, 15, 38)
titleBar.BorderSizePixel = 0
titleBar.Parent = main
corner(titleBar, 14)

local titleL   = Instance.new("TextLabel")
titleL.Size    = UDim2.new(1, -50, 1, 0)
titleL.Position = UDim2.new(0, 14, 0, 0)
titleL.BackgroundTransparency = 1
titleL.Text    = "🛡  Mod Menu"
titleL.TextColor3 = Color3.fromRGB(200, 170, 255)
titleL.Font    = Enum.Font.GothamBold
titleL.TextSize = 20
titleL.TextXAlignment = Enum.TextXAlignment.Left
titleL.Parent  = titleBar

local closeBtn = Instance.new("TextButton")
closeBtn.Size  = UDim2.new(0, 32, 0, 32)
closeBtn.Position = UDim2.new(1, -40, 0.5, 0)
closeBtn.AnchorPoint = Vector2.new(0, 0.5)
closeBtn.BackgroundColor3 = Color3.fromRGB(180, 40, 40)
closeBtn.BorderSizePixel = 0
closeBtn.Text  = "✕"
closeBtn.TextColor3 = Color3.new(1, 1, 1)
closeBtn.Font  = Enum.Font.GothamBold
closeBtn.TextSize = 16
closeBtn.Parent = titleBar
corner(closeBtn, 6)
closeBtn.MouseButton1Click:Connect(function() screen.Enabled = false end)

-- Scroll content
local scroll   = Instance.new("ScrollingFrame")
scroll.Size    = UDim2.new(1, -20, 1, -54)
scroll.Position = UDim2.new(0, 10, 0, 50)
scroll.BackgroundTransparency = 1
scroll.BorderSizePixel = 0
scroll.ScrollBarThickness = 5
scroll.ScrollBarImageColor3 = Color3.fromRGB(120, 90, 200)
scroll.AutomaticCanvasSize = Enum.AutomaticSize.Y
scroll.CanvasSize = UDim2.new(0, 0, 0, 0)
scroll.Parent  = main

local listLayout = Instance.new("UIListLayout")
listLayout.Padding = UDim.new(0, 8)
listLayout.Parent  = scroll

local pad = Instance.new("UIPadding")
pad.PaddingTop = UDim.new(0, 6)
pad.PaddingLeft = UDim.new(0, 4)
pad.PaddingRight = UDim.new(0, 4)
pad.Parent = scroll

local feedback = Instance.new("TextLabel")
feedback.Size  = UDim2.new(1, 0, 0, 26)
feedback.BackgroundColor3 = Color3.fromRGB(20, 40, 20)
feedback.BackgroundTransparency = 0.3
feedback.BorderSizePixel = 0
feedback.Text  = ""
feedback.TextColor3 = Color3.fromRGB(120, 255, 120)
feedback.Font  = Enum.Font.Gotham
feedback.TextSize = 13
feedback.Parent = scroll
corner(feedback, 6)

local function showFeedback(msg, ok)
	feedback.Text = msg
	feedback.TextColor3 = ok
		and Color3.fromRGB(100, 255, 100)
		or  Color3.fromRGB(255, 100, 100)
	feedback.BackgroundColor3 = ok
		and Color3.fromRGB(20, 50, 20)
		or  Color3.fromRGB(50, 20, 20)
end

local function runCmd(cmd, args)
	local ok, msg = ModCommand:InvokeServer(cmd, args or {})
	showFeedback((ok and "✓ " or "✗ ") .. (msg or ""), ok == true)
end

-- ── Section: Target ───────────────────────────────────────────────────────────
newLabel(scroll, "─── Target Player ───", 13, Color3.fromRGB(160, 140, 200))
local targetBox, _ = newInput(scroll, "Player name (leave blank = self)")

-- ── Section: Coins ────────────────────────────────────────────────────────────
newLabel(scroll, "─── Coins ───", 13, Color3.fromRGB(255, 210, 80))
local coinAmtBox, _ = newInput(scroll, "Amount")
local giveCoinsBtn  = newButton(scroll, "🪙 Give Coins", Color3.fromRGB(180, 140, 0))
giveCoinsBtn.MouseButton1Click:Connect(function()
	runCmd("give_coins", {
		target = targetBox.Text ~= "" and targetBox.Text or nil,
		amount = coinAmtBox.Text
	})
end)

-- ── Section: Health ───────────────────────────────────────────────────────────
newLabel(scroll, "─── Health ───", 13, Color3.fromRGB(100, 220, 100))
local hpBox, _   = newInput(scroll, "HP amount")
local setHpBtn   = newButton(scroll, "❤ Set Health", Color3.fromRGB(40, 140, 60))
setHpBtn.MouseButton1Click:Connect(function()
	runCmd("set_health", {target = targetBox.Text ~= "" and targetBox.Text or nil, amount = hpBox.Text})
end)

-- ── Section: God Mode ─────────────────────────────────────────────────────────
newLabel(scroll, "─── God Mode ───", 13, Color3.fromRGB(255, 180, 60))
local godBtn     = newButton(scroll, "☀ Toggle God Mode", Color3.fromRGB(180, 100, 0))
godBtn.MouseButton1Click:Connect(function()
	runCmd("god_mode", {target = targetBox.Text ~= "" and targetBox.Text or nil})
end)

-- ── Section: Speed ────────────────────────────────────────────────────────────
newLabel(scroll, "─── Speed ───", 13, Color3.fromRGB(100, 200, 255))
local speedBox, _ = newInput(scroll, "Speed (default 16)")
local setSpeedBtn = newButton(scroll, "💨 Set Speed", Color3.fromRGB(30, 100, 160))
setSpeedBtn.MouseButton1Click:Connect(function()
	runCmd("speed", {target = targetBox.Text ~= "" and targetBox.Text or nil, amount = speedBox.Text})
end)

-- ── Section: Fly ──────────────────────────────────────────────────────────────
newLabel(scroll, "─── Fly ───", 13, Color3.fromRGB(180, 220, 255))
local flyBtn     = newButton(scroll, "🪁 Toggle Fly", Color3.fromRGB(60, 80, 180))
flyBtn.MouseButton1Click:Connect(function()
	runCmd("fly", {target = targetBox.Text ~= "" and targetBox.Text or nil})
end)

-- ── Section: Teleport ─────────────────────────────────────────────────────────
newLabel(scroll, "─── Teleport ───", 13, Color3.fromRGB(200, 160, 255))
local tpXBox, _  = newInput(scroll, "X")
local tpYBox, _  = newInput(scroll, "Y (height)")
local tpZBox, _  = newInput(scroll, "Z")
local tpBtn      = newButton(scroll, "⚡ Teleport", Color3.fromRGB(100, 60, 180))
tpBtn.MouseButton1Click:Connect(function()
	runCmd("teleport", {
		target = targetBox.Text ~= "" and targetBox.Text or nil,
		x = tpXBox.Text, y = tpYBox.Text ~= "" and tpYBox.Text or "20", z = tpZBox.Text
	})
end)

-- Quick teleport buttons
local quickFrame = Instance.new("Frame")
quickFrame.Size  = UDim2.new(1, 0, 0, 34)
quickFrame.BackgroundTransparency = 1
quickFrame.Parent = scroll

local qLayout    = Instance.new("UIListLayout")
qLayout.FillDirection = Enum.FillDirection.Horizontal
qLayout.Padding  = UDim.new(0, 6)
qLayout.Parent   = quickFrame

local LOCATIONS = {
	{name = "Market", x = 0,    y = 15, z = 0},
	{name = "Arena",  x = 200,  y = 15, z = 200},
	{name = "Shrine", x = -180, y = 15, z = -180},
}
for _, loc in ipairs(LOCATIONS) do
	local b = Instance.new("TextButton")
	b.Size  = UDim2.new(0, 88, 1, 0)
	b.BackgroundColor3 = Color3.fromRGB(50, 40, 80)
	b.BorderSizePixel = 0
	b.Text  = loc.name
	b.TextColor3 = Color3.fromRGB(200, 190, 255)
	b.Font  = Enum.Font.Gotham
	b.TextSize = 12
	b.Parent = quickFrame
	corner(b, 6)
	b.MouseButton1Click:Connect(function()
		runCmd("teleport", {
			target = targetBox.Text ~= "" and targetBox.Text or nil,
			x = tostring(loc.x), y = tostring(loc.y), z = tostring(loc.z)
		})
	end)
end

-- ── Section: Loot ─────────────────────────────────────────────────────────────
newLabel(scroll, "─── Loot ───", 13, Color3.fromRGB(255, 220, 100))
local spawnLootBtn = newButton(scroll, "📦 Spawn Loot Here", Color3.fromRGB(150, 100, 20))
spawnLootBtn.MouseButton1Click:Connect(function()
	runCmd("spawn_loot", {target = targetBox.Text ~= "" and targetBox.Text or nil})
end)

-- ── Section: Player Control ───────────────────────────────────────────────────
newLabel(scroll, "─── Player Control ───", 13, Color3.fromRGB(255, 140, 140))

local resetBtn = newButton(scroll, "🔄 Reset Player", Color3.fromRGB(100, 80, 20))
resetBtn.MouseButton1Click:Connect(function()
	runCmd("reset_player", {target = targetBox.Text ~= "" and targetBox.Text or nil})
end)

local kickBtn  = newButton(scroll, "👢 Kick Player", Color3.fromRGB(160, 40, 40))
kickBtn.MouseButton1Click:Connect(function()
	if targetBox.Text == "" then showFeedback("✗ Specify a target", false); return end
	runCmd("kick", {target = targetBox.Text})
end)

-- ── Fly client-side ───────────────────────────────────────────────────────────
local flyActive  = false
local flyBodyVel, flyBodyGyro

Remotes:WaitForChild("ToggleFly"):Connect and
Remotes.ToggleFly.OnClientEvent:Connect(function(enabled)
	flyActive = enabled
	local char = player.Character
	if not char then return end
	local hrp  = char:FindFirstChild("HumanoidRootPart")
	if not hrp then return end

	if enabled then
		local hum = char:FindFirstChild("Humanoid")
		if hum then hum.PlatformStand = true end

		flyBodyVel         = Instance.new("BodyVelocity")
		flyBodyVel.MaxForce = Vector3.new(1e5, 1e5, 1e5)
		flyBodyVel.Velocity = Vector3.new(0, 0, 0)
		flyBodyVel.Parent   = hrp

		flyBodyGyro        = Instance.new("BodyGyro")
		flyBodyGyro.MaxTorque = Vector3.new(1e5, 1e5, 1e5)
		flyBodyGyro.D      = 100
		flyBodyGyro.CFrame = hrp.CFrame
		flyBodyGyro.Parent = hrp
	else
		local hum = char:FindFirstChild("Humanoid")
		if hum then hum.PlatformStand = false end
		if flyBodyVel then flyBodyVel:Destroy(); flyBodyVel = nil end
		if flyBodyGyro then flyBodyGyro:Destroy(); flyBodyGyro = nil end
	end
end)

local camera = workspace.CurrentCamera
game:GetService("RunService").Heartbeat:Connect(function()
	if not flyActive or not flyBodyVel then return end
	local char = player.Character
	if not char then return end
	local hrp  = char:FindFirstChild("HumanoidRootPart")
	if not hrp then return end

	local speed    = 50
	local moveDir  = Vector3.new(0, 0, 0)
	local camLook  = camera.CFrame.LookVector
	local camRight = camera.CFrame.RightVector

	if UserInputService:IsKeyDown(Enum.KeyCode.W) then
		moveDir = moveDir + camLook
	end
	if UserInputService:IsKeyDown(Enum.KeyCode.S) then
		moveDir = moveDir - camLook
	end
	if UserInputService:IsKeyDown(Enum.KeyCode.A) then
		moveDir = moveDir - camRight
	end
	if UserInputService:IsKeyDown(Enum.KeyCode.D) then
		moveDir = moveDir + camRight
	end
	if UserInputService:IsKeyDown(Enum.KeyCode.Space) then
		moveDir = moveDir + Vector3.new(0, 1, 0)
	end
	if UserInputService:IsKeyDown(Enum.KeyCode.LeftControl) then
		moveDir = moveDir - Vector3.new(0, 1, 0)
	end

	if moveDir.Magnitude > 0 then
		flyBodyVel.Velocity = moveDir.Unit * speed
	else
		flyBodyVel.Velocity = Vector3.new(0, 0, 0)
	end
	flyBodyGyro.CFrame = camera.CFrame
end)

-- ── Toggle: backtick or \ ─────────────────────────────────────────────────────
UserInputService.InputBegan:Connect(function(input, gpe)
	if gpe then return end
	if input.KeyCode == Enum.KeyCode.BackSlash or
	   input.KeyCode == Enum.KeyCode.BackQuote then
		screen.Enabled = not screen.Enabled
		if screen.Enabled then
			TweenService:Create(main, TweenInfo.new(0.2, Enum.EasingStyle.Back), {
				Size = UDim2.new(0, 460, 0, 560)
			}):Play()
		end
	end
end)

-- Open button on HUD
task.delay(1.5, function()
	local hud = player.PlayerGui:WaitForChild("HUD", 5)
	if not hud then return end

	local modBtn = Instance.new("TextButton")
	modBtn.Size  = UDim2.new(0, 120, 0, 34)
	modBtn.Position = UDim2.new(0, 148, 1, -130)
	modBtn.AnchorPoint = Vector2.new(0, 1)
	modBtn.BackgroundColor3 = Color3.fromRGB(80, 30, 130)
	modBtn.BorderSizePixel = 0
	modBtn.Text  = "🛡 Mod [\\ ]"
	modBtn.TextColor3 = Color3.new(1, 1, 1)
	modBtn.Font  = Enum.Font.GothamBold
	modBtn.TextSize = 13
	modBtn.Parent = hud
	local c = Instance.new("UICorner"); c.CornerRadius = UDim.new(0, 8); c.Parent = modBtn
	modBtn.MouseButton1Click:Connect(function()
		screen.Enabled = not screen.Enabled
	end)
end)
