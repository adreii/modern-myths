-- BuildInteriorsPhase2
-- Phase 2 of town-plan.md: interiors inside the phase 1 shells.
--   Hero's house: kitchen + living room downstairs, bedroom upstairs, real stairs (the room kit's
--                 furniture, moved into the house). Garage: workbench, pegboard, half-built go-kart.
--   School:       front hallway with lockers and stairs; cafeteria and hall with a stage behind it;
--                 two classrooms upstairs.
-- Also removes the old Backlot rooms (BuildRoomKit), which this replaces.
-- Run in Edit mode after BuildTownPhase1. Safe to re-run (rebuilds each building's "Interior" model).
--
-- Filming inside: hide the street wall with StoryKit/Sets (Sets.cutaway(building, true)).
-- In the school, the hallway's back wall is also a cutaway ("HallwayWall"), so the cafeteria and
-- the hall can be filmed through it. Camera mounts and character spots go in workspace.Markers
-- (Cam_House_*, Cam_Garage, Cam_School_*, Mark_House_*, Mark_Garage_*, Mark_School_*).

local TRIM = Color3.fromRGB(240, 238, 232)
local WOOD = Color3.fromRGB(150, 105, 70)
local DARK = Color3.fromRGB(40, 40, 46)
local CREAM = Color3.fromRGB(240, 230, 210)

local buildings = workspace.Town.Buildings
local markers = workspace:FindFirstChild("Markers")

-- Remove the old Backlot rooms and their markers.
local backlot = workspace:FindFirstChild("Backlot")
if backlot then
	backlot:Destroy()
end
for _, m in markers:GetChildren() do
	if m.Name:match("_Bedroom") or m.Name:match("_Kitchen") or m.Name:match("_Living")
		or m.Name:match("_House_") or m.Name:match("^Cam_Garage") or m.Name:match("_Garage_") or m.Name:match("_School_") then
		m:Destroy()
	end
end

local function part(parent: Instance, name: string, size: Vector3, cf: CFrame, color: Color3, material: Enum.Material?, shape: Enum.PartType?): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true
	p.Size = size
	p.CFrame = cf
	p.Color = color
	p.Material = material or Enum.Material.SmoothPlastic
	if shape then
		p.Shape = shape
	end
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Parent = parent
	return p
end

local function light(parent: Instance, brightness: number, range: number, color: Color3?)
	local l = Instance.new("PointLight")
	l.Brightness = brightness
	l.Range = range
	l.Color = color or Color3.fromRGB(255, 228, 190)
	l.Parent = parent
end

local function ceilingLamp(parent: Instance, cf: CFrame, brightness: number?, range: number?)
	local lamp = part(parent, "CeilingLamp", Vector3.new(2.4, 0.3, 2.4), cf, Color3.fromRGB(255, 242, 215), Enum.Material.Neon)
	light(lamp, brightness or 1.4, range or 26)
end

local function marker(name: string, pos: Vector3, lookAt: Vector3?)
	local m = Instance.new("Part")
	m.Name = name
	m.Anchored = true
	m.CanCollide = false
	m.CanQuery = false
	m.CanTouch = false
	m.Transparency = 1
	m.Size = Vector3.new(1, 1, 1)
	m.CFrame = if lookAt then CFrame.lookAt(pos, lookAt) else CFrame.new(pos)
	m.Parent = markers
end

local function signText(board: BasePart, text: string, color: Color3, font: Enum.Font?)
	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Front
	gui.PixelsPerStud = 40
	gui.Parent = board
	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Text = text
	label.TextScaled = true
	label.FontFace = Font.fromEnum(font or Enum.Font.GothamBlack)
	label.TextColor3 = color
	label.Parent = gui
end

-- A wall with openings (same idea as phase 1). `bottom` = bottom centre, local X along the wall.
-- Openings { x0, x1, y0, y1 } are left empty (doorways).
local function wallWithGaps(parent: Instance, name: string, bottom: CFrame, width: number, height: number, color: Color3, gaps: { { number } })
	local xs = { -width / 2, width / 2 }
	for _, o in gaps do
		table.insert(xs, o[1])
		table.insert(xs, o[2])
	end
	table.sort(xs)
	local cuts = {}
	for _, x in xs do
		if #cuts == 0 or x - cuts[#cuts] > 1e-3 then
			table.insert(cuts, x)
		end
	end
	for i = 1, #cuts - 1 do
		local a, b = cuts[i], cuts[i + 1]
		local y = 0
		for _, o in gaps do
			if o[1] <= a + 1e-3 and o[2] >= b - 1e-3 then
				if o[3] > y then
					part(parent, name, Vector3.new(b - a, o[3] - y, 1), bottom * CFrame.new((a + b) / 2, (y + o[3]) / 2, 0), color)
				end
				y = math.max(y, o[4])
			end
		end
		if height > y then
			part(parent, name, Vector3.new(b - a, height - y, 1), bottom * CFrame.new((a + b) / 2, (y + height) / 2, 0), color)
		end
	end
end

-- Replace a building's floor slab with one that has a stairwell hole.
-- `L` maps building-local coords to world; the slab spans the inner area at height y (slab centre).
local function slabWithHole(building: Model, slabName: string, L: (number, number, number) -> CFrame, y: number, iw: number, id: number, hole: { number })
	local old = building:FindFirstChild(slabName)
	local color = if old then old.Color else Color3.fromRGB(180, 170, 155)
	if old then
		old:Destroy()
	end
	local slab = Instance.new("Model")
	slab.Name = slabName
	slab.Parent = building
	local x0, x1, z0, z1 = hole[1], hole[2], hole[3], hole[4]
	local function piece(ax: number, bx: number, az: number, bz: number)
		if bx - ax > 1e-3 and bz - az > 1e-3 then
			part(slab, "Slab", Vector3.new(bx - ax, 0.7, bz - az), L((ax + bx) / 2, y, (az + bz) / 2), color, Enum.Material.WoodPlanks)
		end
	end
	piece(-iw / 2, x0, -id / 2, id / 2)
	piece(x1, iw / 2, -id / 2, id / 2)
	piece(x0, x1, -id / 2, z0)
	piece(x0, x1, z1, id / 2)
end

-- Solid stairs rising `rise` over `count` steps. `start` is the CFrame at the bottom of the first
-- step's front edge on the floor, looking up the stairs; each step is `depth` deep and `width` wide.
local function stairs(parent: Instance, start: CFrame, width: number, count: number, rise: number, depth: number, color: Color3)
	local m = Instance.new("Model")
	m.Name = "Stairs"
	m.Parent = parent
	local h = rise / count
	for k = 1, count do
		part(m, "Step", Vector3.new(width, k * h, depth), start * CFrame.new(0, k * h / 2, -(k - 0.5) * depth), color, Enum.Material.WoodPlanks)
	end
end

local function railing(parent: Instance, from: Vector3, to: Vector3, color: Color3)
	local m = Instance.new("Model")
	m.Name = "Railing"
	m.Parent = parent
	local len = (to - from).Magnitude
	local mid = (from + to) / 2
	local cf = CFrame.lookAt(mid, to)
	part(m, "Rail", Vector3.new(0.3, 0.3, len), cf * CFrame.new(0, 3.2, 0), color, Enum.Material.Wood)
	local n = math.max(2, math.floor(len / 2))
	for i = 0, n do
		part(m, "Baluster", Vector3.new(0.2, 3.2, 0.2), CFrame.new(from:Lerp(to, i / n)) * CFrame.new(0, 1.6, 0), color, Enum.Material.Wood)
	end
end

-- Furniture -------------------------------------------------------------------------------

local function table4(parent: Instance, name: string, base: CFrame, w: number, d: number, h: number, color: Color3)
	local m = Instance.new("Model")
	m.Name = name
	m.Parent = parent
	part(m, "Top", Vector3.new(w, 0.4, d), base * CFrame.new(0, h - 0.2, 0), color, Enum.Material.Wood)
	for _, sx in { -1, 1 } do
		for _, sz in { -1, 1 } do
			part(m, "Leg", Vector3.new(0.35, h - 0.4, 0.35), base * CFrame.new(sx * (w / 2 - 0.4), (h - 0.4) / 2, sz * (d / 2 - 0.4)), color, Enum.Material.Wood)
		end
	end
	return m
end

-- A chair looking along its base CFrame's -Z (the back is on its +Z side). `s` scales it (kids' chairs).
local function chair(parent: Instance, base: CFrame, color: Color3, s: number?)
	local k = s or 1
	local m = Instance.new("Model")
	m.Name = "Chair"
	m.Parent = parent
	part(m, "Seat", Vector3.new(2 * k, 0.3, 2 * k), base * CFrame.new(0, 2 * k, 0), color, Enum.Material.Wood)
	part(m, "Back", Vector3.new(2 * k, 2.4 * k, 0.3), base * CFrame.new(0, 3.3 * k, 0.85 * k), color, Enum.Material.Wood)
	for _, sx in { -1, 1 } do
		for _, sz in { -1, 1 } do
			part(m, "Leg", Vector3.new(0.25, 1.85 * k, 0.25), base * CFrame.new(sx * 0.8 * k, 0.93 * k, sz * 0.8 * k), color, Enum.Material.Wood)
		end
	end
end

local function bed(parent: Instance, base: CFrame, blanket: Color3) -- base: floor point at the bed's centre, headboard toward +Z
	local m = Instance.new("Model")
	m.Name = "Bed"
	m.Parent = parent
	part(m, "Frame", Vector3.new(5.6, 1.3, 8.5), base * CFrame.new(0, 0.65, 0), WOOD, Enum.Material.Wood)
	part(m, "Headboard", Vector3.new(6, 4, 0.5), base * CFrame.new(0, 2, 4.2), WOOD, Enum.Material.Wood)
	part(m, "Mattress", Vector3.new(5.2, 0.6, 8), base * CFrame.new(0, 1.6, -0.1), TRIM, Enum.Material.Fabric)
	part(m, "Pillow", Vector3.new(3.8, 0.6, 1.5), base * CFrame.new(0, 2.2, 3.1), Color3.new(1, 1, 1), Enum.Material.Fabric)
	part(m, "Blanket", Vector3.new(5.4, 0.3, 5), base * CFrame.new(0, 2, -1.6), blanket, Enum.Material.Fabric)
	return m
end

local function sofa(parent: Instance, base: CFrame, color: Color3, length: number) -- sits facing base's -Z
	local m = Instance.new("Model")
	m.Name = "Sofa"
	m.Parent = parent
	part(m, "Base", Vector3.new(length, 1.5, 3), base * CFrame.new(0, 0.75, 0), color, Enum.Material.Fabric)
	part(m, "Back", Vector3.new(length, 3.2, 0.9), base * CFrame.new(0, 1.6, 1.9), color, Enum.Material.Fabric)
	part(m, "ArmL", Vector3.new(0.9, 2.3, 3.9), base * CFrame.new(-length / 2 - 0.45, 1.15, 0.45), color, Enum.Material.Fabric)
	part(m, "ArmR", Vector3.new(0.9, 2.3, 3.9), base * CFrame.new(length / 2 + 0.45, 1.15, 0.45), color, Enum.Material.Fabric)
	local cushion = color:Lerp(Color3.new(1, 1, 1), 0.15)
	part(m, "CushionL", Vector3.new(length / 2 - 0.1, 0.5, 2.7), base * CFrame.new(-length / 4, 1.75, -0.1), cushion, Enum.Material.Fabric)
	part(m, "CushionR", Vector3.new(length / 2 - 0.1, 0.5, 2.7), base * CFrame.new(length / 4, 1.75, -0.1), cushion, Enum.Material.Fabric)
	return m
end

-- HERO'S HOUSE ---------------------------------------------------------------------------------
-- Shell: centre (122, 127), front faces -Z, 24 x 22, two storeys of 12. Inner area x -11..11, z -10..10.
do
	local house = buildings.HeroHouse
	local old = house:FindFirstChild("Interior")
	if old then
		old:Destroy()
	end
	local int = Instance.new("Model")
	int.Name = "Interior"
	local function L(x: number, y: number, z: number): CFrame
		return CFrame.new(122 + x, 0.55 + y, 127 + z)
	end
	local function F(x: number, y: number, z: number): CFrame -- ground floor, y from the floor top
		return L(x, 0.35 + y, z)
	end
	local function U(x: number, y: number, z: number): CFrame -- upstairs
		return L(x, 12.35 + y, z)
	end

	-- Stairs along the east wall: up from z = -9 to z = 4, landing in a hole in the upstairs floor.
	slabWithHole(house, "Floor2", L, 12, 22, 20, { 8.3, 11, -9.5, 4.5 })
	stairs(int, F(9.7, 0, -9) * CFrame.Angles(0, math.pi, 0), 2.4, 13, 12, 1, Color3.fromRGB(170, 125, 85))
	railing(int, U(8.1, 0, -9.5).Position, U(8.1, 0, 4.5).Position, TRIM)
	railing(int, U(8.3, 0, -9.7).Position, U(11, 0, -9.7).Position, TRIM)

	-- Partition between kitchen (west) and living room (east), leaving an entry strip at the front.
	wallWithGaps(int, "Partition", F(0, 0, 1.5) * CFrame.Angles(0, math.pi / 2, 0), 17, 11.3, CREAM, {})

	-- Kitchen (x -11..0)
	part(int, "BaseCabinets", Vector3.new(7.5, 3.4, 2.4), F(-6.75, 1.7, 8.6), TRIM, Enum.Material.Wood)
	part(int, "Worktop", Vector3.new(7.9, 0.4, 2.8), F(-6.75, 3.6, 8.5), Color3.fromRGB(70, 72, 78), Enum.Material.Granite)
	part(int, "Sink", Vector3.new(2.4, 0.1, 1.6), F(-5.5, 3.82, 8.5), Color3.fromRGB(170, 175, 180), Enum.Material.Metal)
	part(int, "Tap", Vector3.new(0.25, 1.1, 0.25), F(-5.5, 4.35, 9.4), Color3.fromRGB(190, 195, 200), Enum.Material.Metal)
	for _, o in { Vector2.new(-0.6, -0.5), Vector2.new(0.6, -0.5), Vector2.new(-0.6, 0.5), Vector2.new(0.6, 0.5) } do
		part(int, "Burner", Vector3.new(0.1, 0.9, 0.9), F(-8.9 + o.X, 3.85, 8.5 + o.Y) * CFrame.Angles(0, 0, math.pi / 2), DARK, Enum.Material.Metal, Enum.PartType.Cylinder)
	end
	part(int, "OvenDoor", Vector3.new(2.4, 1.8, 0.1), F(-8.9, 1.6, 7.35), Color3.fromRGB(30, 30, 35), Enum.Material.Glass)
	part(int, "WallCabinet", Vector3.new(2.8, 3, 1.4), F(-9.4, 8.6, 9.2), TRIM, Enum.Material.Wood)
	part(int, "Fridge", Vector3.new(3, 8, 2.8), F(-1.8, 4, 8.5), Color3.fromRGB(205, 210, 215), Enum.Material.Metal)
	part(int, "FridgeHandle", Vector3.new(0.2, 2.4, 0.2), F(-3, 5, 7), DARK, Enum.Material.Metal)
	table4(int, "KitchenTable", F(-5.5, 0, -2), 5, 3.5, 3.2, WOOD)
	for _, c in { { -8.5, -2, -math.pi / 2 }, { -2.5, -2, math.pi / 2 }, { -5.5, -4.6, math.pi }, { -5.5, 0.6, 0 } } do
		chair(int, F(c[1], 0, c[2]) * CFrame.Angles(0, c[3], 0), Color3.fromRGB(200, 90, 70))
	end
	part(int, "FruitBowl", Vector3.new(0.5, 1.4, 1.4), F(-5.5, 3.45, -2) * CFrame.Angles(0, 0, math.pi / 2), TRIM, Enum.Material.SmoothPlastic, Enum.PartType.Cylinder)
	part(int, "Apple", Vector3.new(0.6, 0.6, 0.6), F(-5.7, 3.85, -1.9), Color3.fromRGB(210, 40, 40), Enum.Material.SmoothPlastic, Enum.PartType.Ball)
	part(int, "Orange", Vector3.new(0.6, 0.6, 0.6), F(-5.2, 3.85, -2.2), Color3.fromRGB(245, 150, 30), Enum.Material.SmoothPlastic, Enum.PartType.Ball)
	local pendant = part(int, "PendantShade", Vector3.new(1.6, 0.7, 1.6), F(-5.5, 8.6, -2), Color3.fromRGB(255, 235, 200), Enum.Material.Neon)
	light(pendant, 1, 14)
	part(int, "PendantCord", Vector3.new(0.1, 2.4, 0.1), F(-5.5, 10.1, -2), DARK)
	ceilingLamp(int, F(-5.5, 11.1, 4))

	-- Living room (x 0..11): TV on the partition, sofa facing it, stairs along the east wall
	part(int, "TVStand", Vector3.new(1.6, 2.2, 5), F(1.3, 1.1, -3), WOOD, Enum.Material.Wood)
	part(int, "TV", Vector3.new(0.3, 3.4, 5.4), F(0.85, 4.4, -3), DARK)
	local screen = part(int, "TVScreen", Vector3.new(0.1, 3, 5), F(1.05, 4.4, -3), Color3.fromRGB(20, 30, 45), Enum.Material.Glass)
	screen:SetAttribute("Screen", "Right") -- the SurfaceGui face that looks into the room
	sofa(int, F(5.6, 0, -3) * CFrame.Angles(0, math.pi / 2, 0), Color3.fromRGB(200, 110, 90), 5.2) -- faces -X, toward the TV
	table4(int, "CoffeeTable", F(3.3, 0, -3), 2.2, 3.4, 1.5, WOOD)
	part(int, "Rug", Vector3.new(7, 0.1, 7.5), F(4, 0.05, -3), Color3.fromRGB(220, 200, 150), Enum.Material.Fabric)
	part(int, "Bookshelf", Vector3.new(4.4, 8, 1.4), F(4.5, 4, 9.2), WOOD, Enum.Material.Wood)
	local books = { Color3.fromRGB(200, 60, 60), Color3.fromRGB(60, 120, 200), Color3.fromRGB(240, 190, 60), Color3.fromRGB(90, 170, 100) }
	for row = 0, 2 do
		for i = 0, 3 do
			part(int, "Book", Vector3.new(0.7, 1.6, 1), F(3.2 + i * 0.9, 1.3 + row * 2.6, 8.7), books[((i + row) % #books) + 1])
		end
	end
	part(int, "LampPole", Vector3.new(0.3, 5.6, 0.3), F(1.5, 2.8, 7.8), DARK, Enum.Material.Metal)
	local fl = part(int, "LampShade", Vector3.new(1.4, 1, 1.4), F(1.5, 6, 7.8), Color3.fromRGB(255, 235, 200), Enum.Material.Neon)
	light(fl, 0.8, 11)
	part(int, "PlantPot", Vector3.new(1.4, 1.4, 1.4), F(6.5, 0.7, -8.6) * CFrame.Angles(0, 0, math.pi / 2), Color3.fromRGB(190, 110, 70), Enum.Material.SmoothPlastic, Enum.PartType.Cylinder)
	part(int, "Plant", Vector3.new(2.4, 2.4, 2.4), F(6.5, 2.4, -8.6), Color3.fromRGB(80, 150, 70), Enum.Material.Grass, Enum.PartType.Ball)
	ceilingLamp(int, F(4, 11.1, -1))

	-- Bedroom upstairs (whole floor apart from the stairwell)
	bed(int, U(-5.5, 0, 5.5), Color3.fromRGB(240, 150, 90))
	part(int, "Nightstand", Vector3.new(2, 2.2, 1.8), U(-9.6, 1.1, 8.8), WOOD, Enum.Material.Wood)
	part(int, "LampBase", Vector3.new(0.5, 1, 0.5), U(-9.6, 2.7, 8.8), DARK, Enum.Material.Metal)
	local shade = part(int, "LampShade", Vector3.new(1.2, 0.9, 1.2), U(-9.6, 3.6, 8.8), Color3.fromRGB(255, 230, 180), Enum.Material.Neon)
	light(shade, 0.7, 9)
	part(int, "Wardrobe", Vector3.new(2.4, 8.5, 5), U(-9.6, 4.25, -4), Color3.fromRGB(235, 225, 205), Enum.Material.Wood)
	table4(int, "Desk", U(5, 0, 8.6), 4.5, 2.4, 3.2, Color3.fromRGB(235, 225, 205))
	part(int, "Laptop", Vector3.new(1.6, 0.1, 1.2), U(5, 3.25, 8.6), DARK, Enum.Material.Metal)
	chair(int, U(5, 0, 6.4) * CFrame.Angles(0, math.pi, 0), Color3.fromRGB(90, 140, 200)) -- faces the desk (+Z)
	part(int, "Rug", Vector3.new(7, 0.1, 5), U(0, 0.05, 0.5), Color3.fromRGB(120, 170, 140), Enum.Material.Fabric)
	part(int, "Poster", Vector3.new(3, 4, 0.2), U(0, 6.2, 9.4), Color3.fromRGB(255, 200, 60))
	ceilingLamp(int, U(0, 10.9, 0))
	part(int, "Ceiling", Vector3.new(22, 0.1, 20), L(0, 23.6, 0), Color3.fromRGB(245, 242, 235)) -- hides the roof's red underside

	int.Parent = house

	-- Camera mounts (outside the front, i.e. through the cutaway wall) and character spots
	marker("Cam_House_Kitchen", L(-5.5, 6, -24).Position, F(-5.5, 3, 2).Position)
	marker("Cam_House_Living", L(5, 6, -24).Position, F(4, 3, -1).Position)
	marker("Cam_House_Bedroom", L(0, 18.5, -25).Position, U(-1, 3, 3).Position)
	marker("Cam_House_Dollhouse", L(0, 13, -40).Position, L(0, 11, 0).Position)
	marker("Mark_House_FrontDoor", L(0, 0.35, -13).Position)
	marker("Mark_House_Kitchen", F(-5.5, 0, -6.5).Position)
	marker("Mark_House_Sofa", F(5.4, 1.9, -3).Position)
	marker("Mark_House_TV", F(3, 0, 3).Position)
	marker("Mark_House_Bed", U(-5.5, 1.9, 5).Position)
	marker("Mark_House_Desk", U(5, 0, 6).Position)
end
task.wait()

-- GARAGE ------------------------------------------------------------------------------------
-- Shell: centre (142.5, 129), front faces -Z, 13 x 18, one storey of 10. Inner x -5.5..5.5, z -8..8.
do
	local garage = buildings.Garage
	local old = garage:FindFirstChild("Interior")
	if old then
		old:Destroy()
	end
	local int = Instance.new("Model")
	int.Name = "Interior"
	local function G(x: number, y: number, z: number): CFrame
		return CFrame.new(142.5 + x, 0.9 + y, 129 + z)
	end
	table4(int, "Workbench", G(0, 0, 7), 8, 2.2, 3.4, WOOD)
	part(int, "Pegboard", Vector3.new(8, 3.2, 0.2), G(0, 5.6, 7.9), Color3.fromRGB(200, 170, 120), Enum.Material.Wood)
	part(int, "HammerHandle", Vector3.new(0.25, 1.8, 0.2), G(-2.5, 5.4, 7.7), WOOD, Enum.Material.Wood)
	part(int, "HammerHead", Vector3.new(1, 0.4, 0.3), G(-2.5, 6.3, 7.7), DARK, Enum.Material.Metal)
	part(int, "Wrench", Vector3.new(0.3, 2, 0.15), G(-1, 5.6, 7.7) * CFrame.Angles(0, 0, math.rad(20)), Color3.fromRGB(180, 185, 190), Enum.Material.Metal)
	part(int, "SawBlade", Vector3.new(2.6, 0.8, 0.1), G(1.6, 6, 7.7), Color3.fromRGB(190, 195, 200), Enum.Material.Metal)
	part(int, "SawHandle", Vector3.new(0.8, 0.9, 0.2), G(3.2, 6, 7.7), Color3.fromRGB(200, 60, 50))
	part(int, "Shelf", Vector3.new(2, 0.3, 7), G(-5, 4, -1), WOOD, Enum.Material.Wood)
	part(int, "PaintCan", Vector3.new(1, 1.1, 1.1), G(-5, 4.7, -3) * CFrame.Angles(0, 0, math.pi / 2), Color3.fromRGB(60, 120, 200), Enum.Material.Metal, Enum.PartType.Cylinder)
	part(int, "PaintCan", Vector3.new(1, 1.1, 1.1), G(-5, 4.7, -1.5) * CFrame.Angles(0, 0, math.pi / 2), Color3.fromRGB(230, 190, 50), Enum.Material.Metal, Enum.PartType.Cylinder)
	part(int, "Box", Vector3.new(1.8, 1.4, 2), G(-5, 4.85, 1.5), Color3.fromRGB(190, 150, 100), Enum.Material.Cardboard)
	-- Half-built go-kart (the episode 7 project)
	local kart = Instance.new("Model")
	kart.Name = "GoKart"
	kart.Parent = int
	part(kart, "Chassis", Vector3.new(3, 0.4, 5.5), G(0, 0.9, -1), Color3.fromRGB(220, 60, 50), Enum.Material.Metal)
	for _, o in { Vector2.new(-1.7, -2.8), Vector2.new(1.7, -2.8), Vector2.new(-1.7, 0.8) } do
		part(kart, "Wheel", Vector3.new(0.8, 1.6, 1.6), G(o.X, 0.8, -1 + o.Y), DARK, Enum.Material.Rubber, Enum.PartType.Cylinder)
	end
	part(kart, "LooseWheel", Vector3.new(0.8, 1.6, 1.6), G(2.8, 0.4, 3) * CFrame.Angles(0, 0, math.pi / 2), DARK, Enum.Material.Rubber, Enum.PartType.Cylinder)
	part(kart, "Seat", Vector3.new(2, 1.4, 1.6), G(0, 1.8, 0.3), DARK, Enum.Material.Fabric)
	part(kart, "SteeringColumn", Vector3.new(0.2, 1.4, 0.2), G(0, 1.8, -2.4) * CFrame.Angles(math.rad(-30), 0, 0), Color3.fromRGB(180, 185, 190), Enum.Material.Metal)
	part(kart, "SteeringWheel", Vector3.new(0.2, 1.4, 1.4), G(0, 2.5, -2.8) * CFrame.Angles(0, math.pi / 2, math.rad(60)), DARK, Enum.Material.Rubber, Enum.PartType.Cylinder)
	ceilingLamp(int, G(0, 8.6, 0), 1.3, 20)
	int.Parent = garage
	marker("Cam_Garage", G(0, 5, -22).Position, G(0, 2, 1).Position)
	marker("Mark_Garage_Bench", G(0, 0, 4.8).Position)
	marker("Mark_Garage_Kart", G(-2.6, 0, -1).Position)
end
task.wait()

-- SCHOOL ------------------------------------------------------------------------------------
-- Shell: centre (0, 155), front faces -Z, 80 x 30, two storeys of 12. Inner x -39..39, z -14..14.
-- Ground floor: hallway (z -14..-8, lockers, stairs) | cafeteria (west) and hall with stage (east).
-- Upstairs: Classroom A (west) and Classroom B (east).
do
	local school = buildings.School
	local old = school:FindFirstChild("Interior")
	if old then
		old:Destroy()
	end
	local int = Instance.new("Model")
	int.Name = "Interior"
	local function S(x: number, y: number, z: number): CFrame
		return CFrame.new(x, 0.55 + y, 155 + z)
	end
	local function F(x: number, y: number, z: number): CFrame
		return S(x, 0.35 + y, z)
	end
	local function U(x: number, y: number, z: number): CFrame
		return S(x, 12.35 + y, z)
	end

	-- Stairs in the hallway's west end, rising east; hole in the upstairs floor above them.
	slabWithHole(school, "Floor2", S, 12, 78, 28, { -38.5, -24, -14, -10 })
	stairs(int, F(-38, 0, -12) * CFrame.Angles(0, -math.pi / 2, 0), 3, 13, 12, 1, Color3.fromRGB(150, 150, 155))
	railing(int, U(-38.5, 0, -9.8).Position, U(-24, 0, -9.8).Position, Color3.fromRGB(60, 110, 190))

	-- Hallway back wall (cutaway, so the rooms behind can be filmed), with doorways to both rooms.
	local hallWall = Instance.new("Model")
	hallWall.Name = "HallwayWall"
	hallWall:SetAttribute("Cutaway", true)
	hallWall.Parent = int
	wallWithGaps(hallWall, "Wall", F(0, 0, -8), 78, 11.3, CREAM, { { -20, -15, 0, 8.5 }, { 15, 20, 0, 8.5 } })
	-- Lockers on the hallway side of that wall
	local lockerColors = { Color3.fromRGB(60, 110, 190), Color3.fromRGB(70, 125, 205) }
	local function lockerRun(x0: number, x1: number)
		local i = 0
		for x = x0, x1 - 1.9, 2 do
			i += 1
			part(hallWall, "Locker", Vector3.new(1.9, 7, 1.4), F(x + 0.95, 3.5, -9.2), lockerColors[(i % 2) + 1], Enum.Material.Metal)
			part(hallWall, "Vent", Vector3.new(1.2, 0.8, 0.1), F(x + 0.95, 6, -9.95), DARK, Enum.Material.Metal)
			part(hallWall, "Handle", Vector3.new(0.15, 0.6, 0.15), F(x + 1.6, 3.6, -9.95), Color3.fromRGB(200, 200, 205), Enum.Material.Metal)
		end
	end
	lockerRun(-14, 14)
	lockerRun(21, 38)
	part(int, "HallFloorStripe", Vector3.new(60, 0.05, 0.6), F(0, 0.03, -11), Color3.fromRGB(240, 200, 60))
	for _, x in { -12, 12, 30 } do
		ceilingLamp(int, F(x, 11.1, -11), 1.2, 20)
	end

	-- Divider between cafeteria and hall
	wallWithGaps(int, "Divider", F(0, 0, 3) * CFrame.Angles(0, math.pi / 2, 0), 22, 11.3, CREAM, {})

	-- Cafeteria (x -39..0)
	part(int, "ServingCounter", Vector3.new(20, 3.4, 2.4), F(-20, 1.7, 12.6), Color3.fromRGB(200, 205, 210), Enum.Material.Metal)
	part(int, "CounterTop", Vector3.new(20.4, 0.3, 2.8), F(-20, 3.55, 12.5), Color3.fromRGB(170, 175, 180), Enum.Material.Metal)
	local foods = { Color3.fromRGB(240, 200, 80), Color3.fromRGB(110, 170, 80), Color3.fromRGB(200, 90, 60), Color3.fromRGB(240, 240, 230) }
	for i = 0, 5 do
		part(int, "FoodTray", Vector3.new(2.4, 0.3, 1.6), F(-27.5 + i * 3, 3.85, 12.5), Color3.fromRGB(150, 155, 160), Enum.Material.Metal)
		part(int, "Food", Vector3.new(1.8, 0.4, 1.1), F(-27.5 + i * 3, 4.1, 12.5), foods[(i % #foods) + 1], Enum.Material.SmoothPlastic)
	end
	local menu = part(int, "MenuBoard", Vector3.new(10, 3, 0.2), F(-20, 7.5, 13.85), Color3.fromRGB(40, 60, 50))
	signText(menu, "LUNCH: PIZZA FRIDAY!", Color3.fromRGB(250, 245, 220), Enum.Font.FredokaOne)
	for _, z in { -3.5, 3.5 } do
		table4(int, "LunchTable", F(-20, 0, z), 20, 3.2, 2.8, Color3.fromRGB(230, 225, 210))
		part(int, "Bench", Vector3.new(20, 0.4, 1.1), F(-20, 1.7, z - 2.4), Color3.fromRGB(60, 110, 190))
		part(int, "Bench", Vector3.new(20, 0.4, 1.1), F(-20, 1.7, z + 2.4), Color3.fromRGB(60, 110, 190))
		part(int, "BenchLegs", Vector3.new(18, 1.5, 0.4), F(-20, 0.75, z - 2.4), DARK, Enum.Material.Metal)
		part(int, "BenchLegs", Vector3.new(18, 1.5, 0.4), F(-20, 0.75, z + 2.4), DARK, Enum.Material.Metal)
	end
	for i = 0, 3 do
		part(int, "LunchTrayOnTable", Vector3.new(1.8, 0.2, 1.3), F(-28 + i * 5, 2.9, -3.5 + (if i % 2 == 0 then -0.8 else 0.8)), Color3.fromRGB(240, 120, 90))
	end
	for _, x in { -30, -10 } do
		ceilingLamp(int, F(x, 11.1, 3), 1.3, 26)
	end

	-- Hall with a stage (x 0..39)
	local hall = Instance.new("Model")
	hall.Name = "Hall"
	hall.Parent = int
	part(hall, "Stage", Vector3.new(36, 2.5, 7), F(20, 1.25, 10.5), Color3.fromRGB(150, 105, 70), Enum.Material.WoodPlanks)
	part(hall, "StageLip", Vector3.new(36, 0.4, 0.4), F(20, 2.45, 6.9), Color3.fromRGB(240, 200, 60))
	part(hall, "Backdrop", Vector3.new(36, 8.8, 0.4), F(20, 6.9, 13.7), Color3.fromRGB(120, 30, 40), Enum.Material.Fabric)
	part(hall, "CurtainL", Vector3.new(3, 8.8, 0.6), F(3.5, 6.9, 7.6), Color3.fromRGB(170, 30, 40), Enum.Material.Fabric)
	part(hall, "CurtainR", Vector3.new(3, 8.8, 0.6), F(36.5, 6.9, 7.6), Color3.fromRGB(170, 30, 40), Enum.Material.Fabric)
	local banner = part(hall, "Banner", Vector3.new(16, 2.4, 0.2), F(20, 9.4, 13.4), Color3.fromRGB(250, 245, 230))
	signText(banner, "SCIENCE FAIR", Color3.fromRGB(40, 70, 140))
	part(hall, "Podium", Vector3.new(2.4, 3.4, 1.8), F(20, 4.2, 9.5), WOOD, Enum.Material.Wood)
	part(hall, "Microphone", Vector3.new(0.2, 1, 0.2), F(20, 6.4, 9.1), DARK, Enum.Material.Metal)
	for _, z in { -5, -2, 1 } do
		for x = 8, 32, 3 do
			chair(hall, F(x, 0, z) * CFrame.Angles(0, math.pi, 0), Color3.fromRGB(60, 110, 190), 0.85)
		end
	end
	local spotHousing = part(hall, "Spotlight", Vector3.new(1, 1, 1.4), F(20, 10.8, -2), DARK, Enum.Material.Metal)
	spotHousing.CFrame = CFrame.lookAt(spotHousing.Position, F(20, 4, 9.5).Position)
	local spot = Instance.new("SpotLight")
	spot.Face = Enum.NormalId.Front
	spot.Angle = 35
	spot.Range = 30
	spot.Brightness = 3
	spot.Color = Color3.fromRGB(255, 240, 210)
	spot.Parent = spotHousing
	for _, x in { 10, 30 } do
		ceilingLamp(hall, F(x, 11.1, 0), 1.2, 26)
	end

	-- Upstairs classrooms
	wallWithGaps(int, "ClassDivider", U(0, 0, 0) * CFrame.Angles(0, math.pi / 2, 0), 28, 11.3, CREAM, {})
	local function classroom(cx: number, name: string, boardText: string, deskColor: Color3)
		local room = Instance.new("Model")
		room.Name = name
		room.Parent = int
		local board = part(room, "Whiteboard", Vector3.new(14, 4.6, 0.2), U(cx, 5.6, 13.4), Color3.new(1, 1, 1))
		signText(board, boardText, Color3.fromRGB(40, 70, 160), Enum.Font.FredokaOne) -- PermanentMarker didn't render
		part(room, "BoardFrame", Vector3.new(14.6, 5.2, 0.15), U(cx, 5.6, 13.5), Color3.fromRGB(150, 150, 155), Enum.Material.Metal)
		part(room, "BoardTray", Vector3.new(14, 0.25, 0.6), U(cx, 3.2, 13.2), Color3.fromRGB(150, 150, 155), Enum.Material.Metal)
		table4(room, "TeacherDesk", U(cx + 9, 0, 9), 5, 2.6, 3.2, WOOD)
		part(room, "Apple", Vector3.new(0.6, 0.6, 0.6), U(cx + 10.5, 3.5, 9), Color3.fromRGB(210, 40, 40), Enum.Material.SmoothPlastic, Enum.PartType.Ball)
		part(room, "Clock", Vector3.new(0.2, 2, 2), U(cx - 11, 9, 13.6) * CFrame.Angles(0, math.pi / 2, 0), Color3.new(1, 1, 1), Enum.Material.SmoothPlastic, Enum.PartType.Cylinder)
		for _, z in { -6, -1, 4 } do
			for _, dx in { -13, -6.5, 0, 6.5, 13 } do
				local x = cx + dx
				local inStairwell = x < -23 and z < -9
				if not inStairwell then
					table4(room, "StudentDesk", U(x, 0, z), 2.6, 2, 2.8, deskColor)
					chair(room, U(x, 0, z - 1.8) * CFrame.Angles(0, math.pi, 0), Color3.fromRGB(60, 110, 190), 0.85)
				end
			end
		end
		for _, dx in { -9, 9 } do
			ceilingLamp(room, U(cx + dx, 10.9, 0), 1.2, 24)
		end
	end
	classroom(-20, "ClassroomA", "2 + 2 = ?", Color3.fromRGB(235, 225, 205))
	classroom(20, "ClassroomB", "Be kind :)", Color3.fromRGB(210, 230, 210))

	int.Parent = school

	-- Camera mounts from the schoolyard, through the cutaway front wall
	marker("Cam_School_Hallway", S(0, 6, -30).Position, F(0, 3, -10).Position)
	marker("Cam_School_Cafeteria", S(-20, 7, -30).Position, F(-20, 3, 4).Position)
	marker("Cam_School_Hall", S(20, 8, -30).Position, F(20, 3, 8).Position)
	marker("Cam_School_ClassroomA", S(-20, 18.5, -30).Position, U(-20, 3, 6).Position)
	marker("Cam_School_ClassroomB", S(20, 18.5, -30).Position, U(20, 3, 6).Position)
	marker("Mark_School_Lockers", F(0, 0, -11.5).Position)
	marker("Mark_School_CafeTable", F(-20, 0, -6.4).Position)
	marker("Mark_School_Stage", F(20, 2.5, 8.5).Position)
	marker("Mark_School_Podium", F(20, 2.5, 8.2).Position)
	marker("Mark_School_ClassA_Front", U(-20, 0, 10).Position)
	marker("Mark_School_ClassB_Front", U(20, 0, 10).Position)
end

return "Phase 2 interiors built: Hero's house (kitchen, living room, bedroom, stairs), garage, school (hallway, cafeteria, hall, 2 classrooms)."
