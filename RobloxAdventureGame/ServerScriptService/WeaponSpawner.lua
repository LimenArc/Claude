-- WeaponSpawner Script (ServerScriptService)
-- Creates Tool objects in ServerStorage that the market hands out
local ServerStorage     = game:GetService("ServerStorage")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local GameConfig        = require(ReplicatedStorage:WaitForChild("GameConfig"))

local weaponStore = Instance.new("Folder")
weaponStore.Name   = "Weapons"
weaponStore.Parent = ServerStorage

-- Weapon definitions: visual geometry + stats tag
local WeaponBuilders = {}

local function tag(tool, id, damage, wtype)
	local d   = Instance.new("StringValue"); d.Name = "WeaponId";   d.Value = id;     d.Parent = tool
	local dmg = Instance.new("NumberValue"); dmg.Name = "Damage";   dmg.Value = damage; dmg.Parent = tool
	local wt  = Instance.new("StringValue"); wt.Name = "WeaponType"; wt.Value = wtype;  wt.Parent = tool
end

-- Staff
function WeaponBuilders.weapon_staff(parent)
	local tool       = Instance.new("Tool")
	tool.Name        = "weapon_staff"
	tool.ToolTip     = "Arcane Staff"
	tool.RequiresHandle = true

	local handle     = Instance.new("Part")
	handle.Name      = "Handle"
	handle.Size      = Vector3.new(0.4, 4, 0.4)
	handle.BrickColor = BrickColor.new("Medium blue")
	handle.Material  = Enum.Material.SmoothPlastic
	handle.Parent    = tool

	local orb        = Instance.new("Part")
	orb.Name         = "Orb"
	orb.Shape        = Enum.PartType.Ball
	orb.Size         = Vector3.new(0.9, 0.9, 0.9)
	orb.BrickColor   = BrickColor.new("Cyan")
	orb.Material     = Enum.Material.Neon
	orb.Anchored     = false
	orb.CanCollide   = false
	orb.Parent       = tool

	local weld       = Instance.new("Weld")
	weld.Part0       = handle
	weld.Part1       = orb
	weld.C0          = CFrame.new(0, 2.2, 0)
	weld.Parent      = handle

	tag(tool, "weapon_staff", 35, "magic")
	tool.Parent = parent
	return tool
end

-- Ninja Stars (shuriken)
function WeaponBuilders.weapon_shuriken(parent)
	local tool       = Instance.new("Tool")
	tool.Name        = "weapon_shuriken"
	tool.ToolTip     = "Ninja Stars"
	tool.RequiresHandle = true

	local handle     = Instance.new("Part")
	handle.Name      = "Handle"
	handle.Shape     = Enum.PartType.Ball
	handle.Size      = Vector3.new(0.6, 0.6, 0.6)
	handle.BrickColor = BrickColor.new("Dark grey")
	handle.Material  = Enum.Material.Metal
	handle.Parent    = tool

	-- Star blades
	for i = 0, 3 do
		local blade  = Instance.new("Part")
		blade.Size   = Vector3.new(1.2, 0.08, 0.3)
		blade.BrickColor = BrickColor.new("Mid gray")
		blade.Material   = Enum.Material.Metal
		blade.CanCollide = false
		blade.Parent     = tool
		local w      = Instance.new("Weld")
		w.Part0      = handle
		w.Part1      = blade
		w.C0         = CFrame.Angles(0, math.rad(i * 45), 0) * CFrame.new(0.6, 0, 0)
		w.Parent     = handle
	end

	tag(tool, "weapon_shuriken", 20, "thrown")
	tool.Parent = parent
	return tool
end

-- Katana
function WeaponBuilders.weapon_katana(parent)
	local tool    = Instance.new("Tool")
	tool.Name     = "weapon_katana"
	tool.ToolTip  = "Steel Katana"
	tool.RequiresHandle = true

	local handle  = Instance.new("Part")
	handle.Name   = "Handle"
	handle.Size   = Vector3.new(0.3, 1.2, 0.3)
	handle.BrickColor = BrickColor.new("Reddish brown")
	handle.Material   = Enum.Material.Wood
	handle.Parent     = tool

	local blade   = Instance.new("Part")
	blade.Size    = Vector3.new(0.1, 3.5, 0.3)
	blade.BrickColor = BrickColor.new("Light grey")
	blade.Material   = Enum.Material.Metal
	blade.CanCollide = false
	blade.Parent     = tool

	local weld    = Instance.new("Weld")
	weld.Part0    = handle
	weld.Part1    = blade
	weld.C0       = CFrame.new(0, 2.35, 0)
	weld.Parent   = handle

	local guard   = Instance.new("Part")
	guard.Size    = Vector3.new(0.6, 0.15, 0.6)
	guard.BrickColor = BrickColor.new("Dark grey")
	guard.Material   = Enum.Material.Metal
	guard.CanCollide = false
	guard.Parent     = tool

	local gWeld   = Instance.new("Weld")
	gWeld.Part0   = handle
	gWeld.Part1   = guard
	gWeld.C0      = CFrame.new(0, 0.7, 0)
	gWeld.Parent  = handle

	tag(tool, "weapon_katana", 30, "melee")
	tool.Parent = parent
	return tool
end

-- War Axe
function WeaponBuilders.weapon_greataxe(parent)
	local tool    = Instance.new("Tool")
	tool.Name     = "weapon_greataxe"
	tool.ToolTip  = "War Axe"
	tool.RequiresHandle = true

	local handle  = Instance.new("Part")
	handle.Name   = "Handle"
	handle.Size   = Vector3.new(0.4, 4, 0.4)
	handle.BrickColor = BrickColor.new("Brown")
	handle.Material   = Enum.Material.Wood
	handle.Parent     = tool

	local head    = Instance.new("Part")
	head.Size     = Vector3.new(2, 1.8, 0.3)
	head.BrickColor = BrickColor.new("Mid gray")
	head.Material   = Enum.Material.Metal
	head.CanCollide = false
	head.Parent     = tool

	local weld    = Instance.new("Weld")
	weld.Part0    = handle
	weld.Part1    = head
	weld.C0       = CFrame.new(0.8, 2.2, 0)
	weld.Parent   = handle

	tag(tool, "weapon_greataxe", 50, "melee")
	tool.Parent = parent
	return tool
end

-- Longbow
function WeaponBuilders.weapon_bow(parent)
	local tool    = Instance.new("Tool")
	tool.Name     = "weapon_bow"
	tool.ToolTip  = "Longbow"
	tool.RequiresHandle = true

	local handle  = Instance.new("Part")
	handle.Name   = "Handle"
	handle.Size   = Vector3.new(0.2, 0.2, 0.2)
	handle.Transparency = 1
	handle.Parent = tool

	local bow     = Instance.new("Part")
	bow.Size      = Vector3.new(0.2, 3.5, 0.2)
	bow.BrickColor = BrickColor.new("Brown")
	bow.Material   = Enum.Material.Wood
	bow.CanCollide = false
	bow.Parent     = tool

	local weld    = Instance.new("Weld")
	weld.Part0    = handle
	weld.Part1    = bow
	weld.Parent   = handle

	-- String
	local top     = Instance.new("Part")
	top.Size      = Vector3.new(0.05, 0.05, 1.8)
	top.BrickColor = BrickColor.new("Light grey")
	top.Material   = Enum.Material.SmoothPlastic
	top.CanCollide = false
	top.Parent     = tool
	local tw      = Instance.new("Weld")
	tw.Part0      = bow
	tw.Part1      = top
	tw.C0         = CFrame.new(0, 1.75, 0)
	tw.C1         = CFrame.new(0, 0, -0.9)
	tw.Parent     = bow

	tag(tool, "weapon_bow", 25, "ranged")
	tool.Parent = parent
	return tool
end

-- Build all weapons into ServerStorage
for _, item in ipairs(GameConfig.SHOP.Items) do
	if item.type == "weapon" then
		local builder = WeaponBuilders[item.id]
		if builder then
			builder(weaponStore)
		end
	end
end

-- Remote: give weapon tool to player backpack
local GiveWeapon = Instance.new("RemoteEvent")
GiveWeapon.Name   = "GiveWeapon"
GiveWeapon.Parent = ReplicatedStorage:WaitForChild("Remotes")

local Players = game:GetService("Players")

-- Listen for UnlockWeapon (fired by PlayerManager after purchase)
ReplicatedStorage:WaitForChild("Remotes"):WaitForChild("UnlockWeapon").OnServerEvent = nil -- events don't have OnServerEvent on RE
-- Instead hook via another RE
local WeaponGrantRE = Instance.new("RemoteEvent")
WeaponGrantRE.Name   = "WeaponGrant"
WeaponGrantRE.Parent = ReplicatedStorage.Remotes

ReplicatedStorage.Remotes.UnlockWeapon.OnServerEvent:Connect(function() end) -- dummy, fired to client

-- Server-side grant: called from PlayerManager after purchase
game.ReplicatedStorage.Remotes:WaitForChild("UnlockWeapon").OnServerEvent:Connect(function()
	-- UnlockWeapon fires TO client only; grant tool separately
end)

-- Allow client to request equip by giving tool
GiveWeapon.OnServerEvent:Connect(function(player, weaponId)
	local template = weaponStore:FindFirstChild(weaponId)
	if not template then return end
	local existing = player.Backpack:FindFirstChild(weaponId)
	      or (player.Character and player.Character:FindFirstChild(weaponId))
	if not existing then
		template:Clone().Parent = player.Backpack
	end
end)

print("[WeaponSpawner] All weapons built")
