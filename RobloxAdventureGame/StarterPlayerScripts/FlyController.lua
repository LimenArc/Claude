-- FlyController LocalScript (StarterPlayerScripts)
-- Client fly mode toggled by ToggleFly remote (fired from ModMenu server side)
-- This script ensures the remote exists and is reachable before ModMenu loads
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Remotes = ReplicatedStorage:WaitForChild("Remotes")

-- Ensure ToggleFly remote exists (WeaponSpawner or this script creates it)
if not Remotes:FindFirstChild("ToggleFly") then
	local r    = Instance.new("RemoteEvent")
	r.Name     = "ToggleFly"
	r.Parent   = Remotes
end
