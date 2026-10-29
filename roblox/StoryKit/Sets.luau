--!strict
-- StoryKit/Sets
-- Film inside the town's buildings. Every building's street wall is a Model named "FrontWall" with
-- the attribute Cutaway = true (the school's locker wall, "HallwayWall", too). Hiding it turns the
-- building into a dollhouse set the camera can look into, like a sitcom set.
--
--   local Sets = require(ReplicatedStorage.StoryKit.Sets)
--   Sets.cutaway(workspace.Town.Buildings.HeroHouse, true)                    -- open the house
--   Sets.cutaway(workspace.Town.Buildings.School, true, { "FrontWall" })      -- just the street wall
--   Sets.cutaway(workspace.Town.Buildings.School, true)                       -- street wall + locker wall
--   Sets.reset()                                                              -- close every building again
--
-- Hiding is local to the viewer (client), so it only affects the recording, not the place.

local Sets = {}

-- Things that stick out from the front of a building and would float in front of the lens.
local FRONT_EXTRAS = { Sign = true, Awning = true, Coping = true, Step = true, Portico = true, Column = true, Marquee = true }

local hidden: { BasePart } = {}

local function hide(p: BasePart)
	if p:GetAttribute("BaseTransparency") == nil then
		p:SetAttribute("BaseTransparency", p.Transparency)
	end
	p.Transparency = 1
	p.CastShadow = false
	for _, g in p:GetChildren() do
		if g:IsA("SurfaceGui") then
			g.Enabled = false
		end
	end
	table.insert(hidden, p)
end

local function show(p: BasePart)
	local base = p:GetAttribute("BaseTransparency")
	if typeof(base) == "number" then
		p.Transparency = base
	end
	p.CastShadow = true
	for _, g in p:GetChildren() do
		if g:IsA("SurfaceGui") then
			g.Enabled = true
		end
	end
end

-- Hide (or show) the cutaway walls of one building. `names` limits it to walls with those names.
function Sets.cutaway(building: Instance, on: boolean, names: { string }?)
	for _, d in building:GetDescendants() do
		if d:IsA("Model") and d:GetAttribute("Cutaway") and (not names or table.find(names, d.Name)) then
			for _, p in d:GetDescendants() do
				if p:IsA("BasePart") then
					if on then
						hide(p)
					else
						show(p)
					end
				end
			end
			-- The street wall also takes the sign, awning and other front pieces with it.
			if d.Name == "FrontWall" and d.Parent then
				for _, extra in d.Parent:GetChildren() do
					if extra:IsA("BasePart") and FRONT_EXTRAS[extra.Name] then
						if on then
							hide(extra)
						else
							show(extra)
						end
					end
				end
			end
		end
	end
end

-- Show every wall hidden so far (call at the start of each shot's setup).
function Sets.reset()
	for _, p in hidden do
		if p.Parent then
			show(p)
		end
	end
	table.clear(hidden)
end

return Sets
