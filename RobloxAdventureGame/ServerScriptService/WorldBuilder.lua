-- WorldBuilder Script (ServerScriptService)
local Workspace = game:GetService("Workspace")
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local GameConfig = require(ReplicatedStorage:WaitForChild("GameConfig"))

local WorldBuilder = {}

-- Lighting setup
local function setupLighting()
	local cfg = GameConfig.LIGHTING
	Lighting.Ambient        = cfg.Ambient
	Lighting.OutdoorAmbient = cfg.OutdoorAmbient
	Lighting.Brightness     = cfg.Brightness
	Lighting.ClockTime      = cfg.ClockTime
	Lighting.FogEnd         = cfg.FogEnd
	Lighting.FogColor       = cfg.FogColor
	Lighting.ShadowSoftness = cfg.ShadowSoftness
	Lighting.GlobalShadows  = true

	local atmosphere = Instance.new("Atmosphere")
	atmosphere.Density     = 0.3
	atmosphere.Offset      = 0.1
	atmosphere.Color       = Color3.fromRGB(170, 190, 215)
	atmosphere.Decay       = Color3.fromRGB(90, 110, 140)
	atmosphere.Glare       = 0.3
	atmosphere.Haze        = 1.5
	atmosphere.Parent      = Lighting

	local bloom = Instance.new("BloomEffect")
	bloom.Intensity  = 0.4
	bloom.Size       = 24
	bloom.Threshold  = 0.95
	bloom.Parent     = Lighting

	local colorCorrect = Instance.new("ColorCorrectionEffect")
	colorCorrect.Saturation = 0.1
	colorCorrect.Contrast   = 0.05
	colorCorrect.Brightness = 0.02
	colorCorrect.Parent     = Lighting

	local sunRays = Instance.new("SunRaysEffect")
	sunRays.Intensity  = 0.08
	sunRays.Spread     = 0.5
	sunRays.Parent     = Lighting

	-- Skybox
	local sky = Instance.new("Sky")
	sky.SkyboxBk = "rbxassetid://159454299"
	sky.SkyboxDn = "rbxassetid://159454296"
	sky.SkyboxFt = "rbxassetid://159454293"
	sky.SkyboxLf = "rbxassetid://159454291"
	sky.SkyboxRt = "rbxassetid://159454286"
	sky.SkyboxUp = "rbxassetid://159454283"
	sky.StarCount = 3000
	sky.Parent    = Lighting
end

-- Terrain generation
local function generateTerrain()
	local terrain = Workspace.Terrain
	terrain:Clear()

	local size = GameConfig.WORLD.Size
	local waterLevel = GameConfig.WORLD.WaterLevel
	local regionSize = 4
	local half = size / 2

	-- Water base
	local waterRegion = Region3.new(
		Vector3.new(-half, -20, -half),
		Vector3.new(half, waterLevel, half)
	)
	terrain:FillBlock(
		CFrame.new(0, (waterLevel - 20) / 2, 0),
		Vector3.new(size, waterLevel + 20, size),
		Enum.Material.Water
	)

	-- Heightmap using noise
	local noiseScale  = 0.008
	local heightScale = 55
	local detailScale = 0.04
	local detailAmp   = 8

	for x = -half, half - regionSize, regionSize do
		for z = -half, half - regionSize, regionSize do
			local nx = x * noiseScale
			local nz = z * noiseScale
			local baseHeight = math.noise(nx, nz, 0.5) * heightScale
			local detail     = math.noise(x * detailScale, z * detailScale, 1.5) * detailAmp
			local height     = baseHeight + detail + 18

			local mat
			if height < waterLevel + 2 then
				mat = Enum.Material.Sand
			elseif height < 25 then
				mat = Enum.Material.Grass
			elseif height < 40 then
				mat = Enum.Material.LeafyGrass
			else
				mat = Enum.Material.Rock
			end

			terrain:FillBlock(
				CFrame.new(x + regionSize/2, height / 2, z + regionSize/2),
				Vector3.new(regionSize, height, regionSize),
				mat
			)
		end
	end
end

-- Place decorations (trees, rocks, bushes)
local function placeDecorations()
	local decorFolder = Instance.new("Folder")
	decorFolder.Name   = "Decorations"
	decorFolder.Parent = Workspace

	local size    = GameConfig.WORLD.Size / 2
	local treeDen = GameConfig.WORLD.TreeDensity
	local rockDen = GameConfig.WORLD.RockDensity
	local count   = 0

	local function raycastHeight(x, z)
		local rayOrigin = Vector3.new(x, 200, z)
		local rayDir    = Vector3.new(0, -400, 0)
		local params    = RaycastParams.new()
		params.FilterType = Enum.RaycastFilterType.Include
		params.FilterDescendantsInstances = {Workspace.Terrain}
		local result = Workspace:Raycast(rayOrigin, rayDir, params)
		return result and result.Position or nil
	end

	local function makeTree(pos)
		local model  = Instance.new("Model")
		model.Name   = "Tree"

		local trunkH = math.random(10, 18)
		local trunk  = Instance.new("Part")
		trunk.Name        = "Trunk"
		trunk.Anchored    = true
		trunk.Size        = Vector3.new(2, trunkH, 2)
		trunk.Position    = pos + Vector3.new(0, trunkH / 2, 0)
		trunk.BrickColor  = BrickColor.new("Brown")
		trunk.Material    = Enum.Material.Wood
		trunk.Parent      = model

		local leafSize = math.random(7, 12)
		local leaves   = Instance.new("Part")
		leaves.Name        = "Leaves"
		leaves.Anchored    = true
		leaves.Shape       = Enum.PartType.Ball
		leaves.Size        = Vector3.new(leafSize, leafSize * 1.2, leafSize)
		leaves.Position    = pos + Vector3.new(0, trunkH + leafSize * 0.4, 0)
		leaves.BrickColor  = BrickColor.new("Bright green")
		leaves.Material    = Enum.Material.Grass
		leaves.CastShadow  = true
		leaves.Parent      = model

		model.Parent = decorFolder
	end

	local function makeRock(pos)
		local rock     = Instance.new("Part")
		rock.Anchored  = true
		rock.Shape     = Enum.PartType.Block
		local s        = math.random(3, 8)
		rock.Size      = Vector3.new(s, s * 0.7, s * 0.9)
		rock.CFrame    = CFrame.new(pos + Vector3.new(0, s * 0.35, 0))
		              * CFrame.Angles(0, math.random() * math.pi, 0)
		rock.BrickColor = BrickColor.new("Medium stone grey")
		rock.Material   = Enum.Material.Rock
		rock.Parent     = decorFolder
	end

	local function makeBush(pos)
		local bush    = Instance.new("Part")
		bush.Anchored = true
		bush.Shape    = Enum.PartType.Ball
		local s       = math.random(2, 4)
		bush.Size     = Vector3.new(s, s * 0.8, s)
		bush.Position = pos + Vector3.new(0, s * 0.4, 0)
		bush.BrickColor = BrickColor.new("Bright green")
		bush.Material   = Enum.Material.Grass
		bush.Parent     = decorFolder
	end

	math.randomseed(12345)
	local attempts = 0
	while count < 300 and attempts < 3000 do
		attempts += 1
		local x = math.random(-size + 20, size - 20)
		local z = math.random(-size + 20, size - 20)
		local pos = raycastHeight(x, z)
		if pos and pos.Y > GameConfig.WORLD.WaterLevel + 2 then
			local r = math.random()
			if r < treeDen then
				makeTree(pos)
				count += 1
			elseif r < treeDen + rockDen then
				makeRock(pos)
				count += 1
			elseif r < treeDen + rockDen + 0.15 then
				makeBush(pos)
				count += 1
			end
		end
	end
end

-- Landmarks / POIs
local function buildLandmarks()
	local folder = Instance.new("Folder")
	folder.Name   = "Landmarks"
	folder.Parent = Workspace

	local function makePlatform(pos, size, color, name)
		local base     = Instance.new("Part")
		base.Anchored  = true
		base.Size      = Vector3.new(size, 3, size)
		base.CFrame    = CFrame.new(pos)
		base.BrickColor = BrickColor.new(color)
		base.Material   = Enum.Material.SmoothPlastic
		base.Name       = name
		base.Parent     = folder

		-- Edge trim
		for _, offset in ipairs({
			Vector3.new(size/2, 0, 0), Vector3.new(-size/2, 0, 0),
			Vector3.new(0, 0, size/2), Vector3.new(0, 0, -size/2),
		}) do
			local trim    = Instance.new("Part")
			trim.Anchored = true
			trim.Size     = Vector3.new(2, 4, size)
			if offset.X ~= 0 then
				trim.Size = Vector3.new(size, 4, 2)
			end
			trim.CFrame    = CFrame.new(pos + offset + Vector3.new(0, 0.5, 0))
			trim.BrickColor = BrickColor.new("Dark grey")
			trim.Material   = Enum.Material.SmoothPlastic
			trim.Parent     = folder
		end
		return base
	end

	-- Market platform
	makePlatform(Vector3.new(0, 12, 0), 60, "Bright yellow", "MarketArea")

	-- Arena
	makePlatform(Vector3.new(200, 10, 200), 80, "Crimson", "Arena")

	-- Shrine
	makePlatform(Vector3.new(-180, 10, -180), 40, "Medium blue", "Shrine")

	-- Outpost towers
	local towerPositions = {
		Vector3.new(150, 12, -150),
		Vector3.new(-150, 12, 150),
	}
	for _, tpos in ipairs(towerPositions) do
		local base = Instance.new("Part")
		base.Anchored = true
		base.Size     = Vector3.new(12, 30, 12)
		base.CFrame   = CFrame.new(tpos + Vector3.new(0, 15, 0))
		base.BrickColor = BrickColor.new("Dark grey")
		base.Material   = Enum.Material.SmoothPlastic
		base.Parent     = folder

		local top = Instance.new("Part")
		top.Anchored  = true
		top.Size      = Vector3.new(16, 4, 16)
		top.CFrame    = CFrame.new(tpos + Vector3.new(0, 32, 0))
		top.BrickColor = BrickColor.new("Dark stone grey")
		top.Material   = Enum.Material.SmoothPlastic
		top.Parent     = folder
	end

	-- Spawn platform
	local spawn = Instance.new("Part")
	spawn.Name     = "SpawnIsland"
	spawn.Anchored = true
	spawn.Size     = Vector3.new(40, 2, 40)
	spawn.CFrame   = CFrame.new(0, 8, 0)
	spawn.BrickColor = BrickColor.new("Bright green")
	spawn.Material   = Enum.Material.Grass
	spawn.Parent     = folder
end

-- Setup spawn point
local function setupSpawn()
	local existing = Workspace:FindFirstChild("SpawnLocation")
	if not existing then
		local spawn = Instance.new("SpawnLocation")
		spawn.Anchored    = true
		spawn.Size        = Vector3.new(20, 1, 20)
		spawn.CFrame      = CFrame.new(0, 10, 0)
		spawn.BrickColor  = BrickColor.new("Bright green")
		spawn.Material    = Enum.Material.SmoothPlastic
		spawn.Duration    = 0
		spawn.Parent      = Workspace
	end
end

-- Build world
setupLighting()
generateTerrain()
placeDecorations()
buildLandmarks()
setupSpawn()
print("[WorldBuilder] World generation complete")
