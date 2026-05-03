-- MarketUI LocalScript (StarterGui)
local Players           = game:GetService("Players")
local TweenService      = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService  = game:GetService("UserInputService")

local player   = Players.LocalPlayer
local Remotes  = ReplicatedStorage:WaitForChild("Remotes")
local BuyItem  = Remotes:WaitForChild("BuyItem")
local GameConfig = require(ReplicatedStorage:WaitForChild("GameConfig"))

local screen   = Instance.new("ScreenGui")
screen.Name    = "MarketUI"
screen.ResetOnSpawn = false
screen.Enabled = false
screen.Parent  = player.PlayerGui

-- ── Helper ────────────────────────────────────────────────────────────────────
local function corner(p, r)
	local c = Instance.new("UICorner"); c.CornerRadius = UDim.new(0, r or 8); c.Parent = p
end
local function stroke(p, t, col)
	local s = Instance.new("UIStroke"); s.Thickness = t or 2
	s.Color = col or Color3.fromRGB(60, 60, 80); s.Parent = p
end
local function pad(p, x, y)
	local u = Instance.new("UIPadding")
	u.PaddingLeft = UDim.new(0, x); u.PaddingRight  = UDim.new(0, x)
	u.PaddingTop  = UDim.new(0, y); u.PaddingBottom = UDim.new(0, y)
	u.Parent = p
end

-- ── Main frame ────────────────────────────────────────────────────────────────
local backdrop = Instance.new("Frame")
backdrop.Name  = "Backdrop"
backdrop.Size  = UDim2.new(1, 0, 1, 0)
backdrop.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
backdrop.BackgroundTransparency = 0.45
backdrop.BorderSizePixel = 0
backdrop.Parent = screen

local main     = Instance.new("Frame")
main.Name      = "Market"
main.Size      = UDim2.new(0, 700, 0, 520)
main.Position  = UDim2.new(0.5, 0, 0.5, 0)
main.AnchorPoint = Vector2.new(0.5, 0.5)
main.BackgroundColor3 = Color3.fromRGB(15, 15, 22)
main.BorderSizePixel = 0
main.Parent    = screen
corner(main, 16)
stroke(main, 2, Color3.fromRGB(80, 60, 150))

-- Title bar
local titleBar = Instance.new("Frame")
titleBar.Size  = UDim2.new(1, 0, 0, 50)
titleBar.BackgroundColor3 = Color3.fromRGB(25, 20, 45)
titleBar.BorderSizePixel = 0
titleBar.Parent = main
corner(titleBar, 16)

local titleLabel = Instance.new("TextLabel")
titleLabel.Size  = UDim2.new(1, -60, 1, 0)
titleLabel.Position = UDim2.new(0, 16, 0, 0)
titleLabel.BackgroundTransparency = 1
titleLabel.Text  = "⚔  Adventure Market"
titleLabel.TextColor3 = Color3.fromRGB(220, 200, 255)
titleLabel.Font  = Enum.Font.GothamBold
titleLabel.TextSize = 22
titleLabel.TextXAlignment = Enum.TextXAlignment.Left
titleLabel.Parent = titleBar

-- Close button
local closeBtn = Instance.new("TextButton")
closeBtn.Size  = UDim2.new(0, 36, 0, 36)
closeBtn.Position = UDim2.new(1, -46, 0, 7)
closeBtn.BackgroundColor3 = Color3.fromRGB(200, 50, 50)
closeBtn.BorderSizePixel = 0
closeBtn.Text  = "✕"
closeBtn.TextColor3 = Color3.new(1, 1, 1)
closeBtn.Font  = Enum.Font.GothamBold
closeBtn.TextSize = 18
closeBtn.Parent = titleBar
corner(closeBtn, 6)

-- Coin display
local coinDisplay = Instance.new("TextLabel")
coinDisplay.Size  = UDim2.new(0, 160, 0, 30)
coinDisplay.Position = UDim2.new(0, 16, 0, 54)
coinDisplay.BackgroundTransparency = 1
coinDisplay.Text  = "🪙 Coins: 0"
coinDisplay.TextColor3 = Color3.fromRGB(255, 220, 0)
coinDisplay.Font  = Enum.Font.GothamBold
coinDisplay.TextSize = 16
coinDisplay.TextXAlignment = Enum.TextXAlignment.Left
coinDisplay.Parent = main

-- Tabs
local tabBar   = Instance.new("Frame")
tabBar.Size    = UDim2.new(1, -32, 0, 36)
tabBar.Position = UDim2.new(0, 16, 0, 88)
tabBar.BackgroundTransparency = 1
tabBar.Parent  = main

local tabLayout = Instance.new("UIListLayout")
tabLayout.FillDirection = Enum.FillDirection.Horizontal
tabLayout.Padding = UDim.new(0, 8)
tabLayout.Parent = tabBar

local TABS      = {"All", "Moves", "Weapons"}
local tabButtons = {}
local activeTab  = "All"

for _, tabName in ipairs(TABS) do
	local btn  = Instance.new("TextButton")
	btn.Size   = UDim2.new(0, 90, 1, 0)
	btn.BackgroundColor3 = Color3.fromRGB(30, 25, 50)
	btn.BorderSizePixel = 0
	btn.Text   = tabName
	btn.TextColor3 = Color3.fromRGB(180, 180, 200)
	btn.Font   = Enum.Font.GothamBold
	btn.TextSize = 14
	btn.Parent = tabBar
	corner(btn, 8)
	stroke(btn, 1, Color3.fromRGB(80, 60, 130))
	tabButtons[tabName] = btn
end

-- Item grid
local scrollFrame = Instance.new("ScrollingFrame")
scrollFrame.Size  = UDim2.new(1, -32, 1, -140)
scrollFrame.Position = UDim2.new(0, 16, 0, 132)
scrollFrame.BackgroundTransparency = 1
scrollFrame.BorderSizePixel = 0
scrollFrame.ScrollBarThickness = 6
scrollFrame.ScrollBarImageColor3 = Color3.fromRGB(100, 80, 160)
scrollFrame.AutomaticCanvasSize = Enum.AutomaticSize.Y
scrollFrame.CanvasSize = UDim2.new(0, 0, 0, 0)
scrollFrame.Parent = main

local gridLayout  = Instance.new("UIGridLayout")
gridLayout.CellSize = UDim2.new(0, 190, 0, 140)
gridLayout.CellPaddingH = UDim.new(0, 10)
gridLayout.CellPaddingV = UDim.new(0, 10)
gridLayout.Parent = scrollFrame

local ownedItems  = {}
local itemCards   = {}

local function getCoins()
	local ls = player:FindFirstChild("leaderstats")
	return ls and ls.Coins and ls.Coins.Value or 0
end

local function buildItemCard(item)
	local card     = Instance.new("Frame")
	card.Name      = item.id
	card.BackgroundColor3 = Color3.fromRGB(22, 20, 35)
	card.BorderSizePixel = 0
	card.Parent    = scrollFrame
	corner(card, 10)
	stroke(card, 1, item.type == "move" and Color3.fromRGB(60, 100, 200)
	                                     or Color3.fromRGB(200, 100, 40))
	pad(card, 8, 6)

	local nameLabel = Instance.new("TextLabel")
	nameLabel.Size  = UDim2.new(1, 0, 0, 24)
	nameLabel.BackgroundTransparency = 1
	nameLabel.Text  = item.display
	nameLabel.TextColor3 = Color3.new(1, 1, 1)
	nameLabel.Font  = Enum.Font.GothamBold
	nameLabel.TextSize = 14
	nameLabel.TextWrapped = true
	nameLabel.Parent = card

	local typeTag  = Instance.new("TextLabel")
	typeTag.Size   = UDim2.new(0, 60, 0, 18)
	typeTag.Position = UDim2.new(0, 0, 0, 26)
	typeTag.BackgroundColor3 = item.type == "move"
		and Color3.fromRGB(40, 80, 180) or Color3.fromRGB(160, 80, 20)
	typeTag.BorderSizePixel = 0
	typeTag.Text   = item.type:upper()
	typeTag.TextColor3 = Color3.new(1, 1, 1)
	typeTag.Font   = Enum.Font.GothamBold
	typeTag.TextSize = 11
	typeTag.Parent = card
	corner(typeTag, 4)

	local descLabel = Instance.new("TextLabel")
	descLabel.Size  = UDim2.new(1, 0, 0, 36)
	descLabel.Position = UDim2.new(0, 0, 0, 48)
	descLabel.BackgroundTransparency = 1
	descLabel.Text  = item.desc or ""
	descLabel.TextColor3 = Color3.fromRGB(180, 175, 190)
	descLabel.Font  = Enum.Font.Gotham
	descLabel.TextSize = 12
	descLabel.TextWrapped = true
	descLabel.Parent = card

	local buyBtn   = Instance.new("TextButton")
	buyBtn.Size    = UDim2.new(1, 0, 0, 28)
	buyBtn.Position = UDim2.new(0, 0, 1, -28)
	buyBtn.AnchorPoint = Vector2.new(0, 1)
	buyBtn.BackgroundColor3 = Color3.fromRGB(60, 200, 80)
	buyBtn.BorderSizePixel = 0
	buyBtn.Text    = "🪙 " .. item.cost
	buyBtn.TextColor3 = Color3.new(1, 1, 1)
	buyBtn.Font    = Enum.Font.GothamBold
	buyBtn.TextSize = 15
	buyBtn.Parent  = card
	corner(buyBtn, 8)

	local function refreshButton()
		if ownedItems[item.id] then
			buyBtn.Text = "✓ Owned"
			buyBtn.BackgroundColor3 = Color3.fromRGB(40, 40, 60)
			buyBtn.Active = false
		elseif getCoins() < item.cost then
			buyBtn.BackgroundColor3 = Color3.fromRGB(120, 50, 50)
			buyBtn.Active = true
		else
			buyBtn.BackgroundColor3 = Color3.fromRGB(60, 200, 80)
			buyBtn.Active = true
		end
	end
	refreshButton()

	buyBtn.MouseButton1Click:Connect(function()
		if ownedItems[item.id] then return end
		local ok, msg = BuyItem:InvokeServer(item.id)
		if ok then
			ownedItems[item.id] = true
			_G.ShowNotif and _G.ShowNotif("Purchased: " .. item.display, Color3.fromRGB(0, 200, 100))
		else
			_G.ShowNotif and _G.ShowNotif("Failed: " .. (msg or "?"), Color3.fromRGB(200, 50, 50))
		end
		refreshButton()
	end)

	itemCards[item.id] = {card = card, refresh = refreshButton, item = item}
	return card
end

local function applyTab(tab)
	activeTab = tab
	for _, entry in pairs(itemCards) do
		local show = tab == "All"
			or (tab == "Moves" and entry.item.type == "move")
			or (tab == "Weapons" and entry.item.type == "weapon")
		entry.card.Visible = show
	end
	for name, btn in pairs(tabButtons) do
		btn.BackgroundColor3 = name == tab
			and Color3.fromRGB(70, 55, 120)
			or  Color3.fromRGB(30, 25, 50)
	end
end

for _, item in ipairs(GameConfig.SHOP.Items) do
	buildItemCard(item)
end
applyTab("All")

for tabName, btn in pairs(tabButtons) do
	btn.MouseButton1Click:Connect(function() applyTab(tabName) end)
end

-- Refresh coins display
Remotes:WaitForChild("UpdateCoins").OnClientEvent:Connect(function(coins)
	coinDisplay.Text = "🪙 Coins: " .. tostring(coins)
	for _, entry in pairs(itemCards) do
		entry.refresh()
	end
end)

-- UnlockMove/Weapon -> mark owned
Remotes:WaitForChild("UnlockMove").OnClientEvent:Connect(function(moveId)
	ownedItems[moveId] = true
	if itemCards[moveId] then itemCards[moveId].refresh() end
end)
Remotes:WaitForChild("UnlockWeapon").OnClientEvent:Connect(function(weaponId)
	ownedItems[weaponId] = true
	if itemCards[weaponId] then itemCards[weaponId].refresh() end
end)

-- Toggle
local function setOpen(open)
	screen.Enabled = open
	if open then
		local tweenIn = TweenService:Create(main, TweenInfo.new(0.25, Enum.EasingStyle.Back), {
			Size = UDim2.new(0, 700, 0, 520)
		})
		main.Size = UDim2.new(0, 500, 0, 350)
		tweenIn:Play()
	end
end

closeBtn.MouseButton1Click:Connect(function() setOpen(false) end)
backdrop.MouseButton1Click:Connect(function() setOpen(false) end)

-- Proximity trigger: open near MarketArea landmark
local RunService = game:GetService("RunService")
RunService.Heartbeat:Connect(function()
	local char = player.Character
	if not char then return end
	local hrp  = char:FindFirstChild("HumanoidRootPart")
	if not hrp then return end
	local market = workspace:FindFirstChild("Landmarks") and
	               workspace.Landmarks:FindFirstChild("MarketArea")
	if market then
		local dist = (hrp.Position - market.Position).Magnitude
		if dist < 40 and not screen.Enabled then
			setOpen(true)
		elseif dist > 50 and screen.Enabled then
			setOpen(false)
		end
	end
end)

-- Also allow M key toggle
UserInputService.InputBegan:Connect(function(input, gpe)
	if gpe then return end
	if input.KeyCode == Enum.KeyCode.M then
		setOpen(not screen.Enabled)
	end
end)

-- Open button on HUD
task.delay(1, function()
	local hud = player.PlayerGui:FindFirstChild("HUD")
	if not hud then return end

	local openBtn = Instance.new("TextButton")
	openBtn.Size  = UDim2.new(0, 120, 0, 34)
	openBtn.Position = UDim2.new(0, 20, 1, -130)
	openBtn.AnchorPoint = Vector2.new(0, 1)
	openBtn.BackgroundColor3 = Color3.fromRGB(70, 50, 130)
	openBtn.BorderSizePixel = 0
	openBtn.Text  = "⚔ Market [M]"
	openBtn.TextColor3 = Color3.new(1, 1, 1)
	openBtn.Font  = Enum.Font.GothamBold
	openBtn.TextSize = 13
	openBtn.Parent = hud
	local c = Instance.new("UICorner"); c.CornerRadius = UDim.new(0, 8); c.Parent = openBtn
	openBtn.MouseButton1Click:Connect(function()
		setOpen(not screen.Enabled)
	end)
end)
