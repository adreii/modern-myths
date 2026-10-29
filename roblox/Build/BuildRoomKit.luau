-- BuildRoomKit
-- The home room kit for the Backlot: three open-front rooms side by side east of town (x = 300 to 380):
-- a bedroom, a kitchen and a living room. Every room comes from one shared shell (floor, walls with
-- a window, a side door, ceiling, lights), then a furniture preset. A new room type (bathroom,
-- classroom, garage) is a new furnish function plus one makeRoom call.
-- Run in Edit mode (Studio MCP execute_luau or the Command Bar). Safe to re-run.
--
-- Rooms are 24 wide (X) x 18 deep (Z) x 12 high, floor top at y = 0.55, open on the +Z side.
-- Adds to workspace.Markers:
--   Cam_<Room>_Wide, Cam_<Room>_Close   camera mounts aimed into the room
--   Mark_<Room>_*                        ground spots for Puppet.place (or a surface, e.g. the bed)

local ROOM_W, ROOM_D, ROOM_H = 24, 18, 12
local FLOOR_TOP = 0.55
local WALL = 1

local backlot = workspace:FindFirstChild("Backlot")
if not backlot then
	backlot = Instance.new("Folder")
	backlot.Name = "Backlot"
	backlot.Parent = workspace
end
local old = backlot:FindFirstChild("HomeRooms")
if old then
	old:Destroy()
end
local home = Instance.new("Folder")
home.Name = "HomeRooms"
home.Parent = backlot

local markers = workspace:FindFirstChild("Markers")
if not markers then
	markers = Instance.new("Folder")
	markers.Name = "Markers"
	markers.Parent = workspace
end
for _, m in markers:GetChildren() do
	if m.Name:match("_Bedroom") or m.Name:match("_Kitchen") or m.Name:match("_Living") then
		m:Destroy()
	end
end

local WHITE = Color3.fromRGB(240, 238, 232)
local WOOD = Color3.fromRGB(150, 105, 70)
local DARK = Color3.fromRGB(40, 40, 46)

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
	l.Color = color or Color3.fromRGB(255, 225, 185)
	l.Shadows = true
	l.Parent = parent
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

-- A simple 4-legged piece (table, desk, nightstand top) centred at `base` (a CFrame on the floor).
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

-- A chair facing along the base CFrame's look direction.
local function chair(parent: Instance, base: CFrame, color: Color3)
	local m = Instance.new("Model")
	m.Name = "Chair"
	m.Parent = parent
	part(m, "Seat", Vector3.new(2, 0.3, 2), base * CFrame.new(0, 2, 0), color, Enum.Material.Wood)
	part(m, "Back", Vector3.new(2, 2.4, 0.3), base * CFrame.new(0, 3.3, 0.85), color, Enum.Material.Wood)
	for _, sx in { -1, 1 } do
		for _, sz in { -1, 1 } do
			part(m, "Leg", Vector3.new(0.25, 1.85, 0.25), base * CFrame.new(sx * 0.8, 0.93, sz * 0.8), color, Enum.Material.Wood)
		end
	end
end

-- The shared shell. Returns the room model and `at(x, y, z)`: a CFrame in room space
-- (x across, y up from the floor top, z from -9 at the back wall to +9 at the open front).
local function makeRoom(name: string, cx: number, wallColor: Color3, floorColor: Color3, floorMaterial: Enum.Material, winX: number)
	local room = Instance.new("Model")
	room.Name = name
	room.Parent = home
	local function at(x: number, y: number, z: number): CFrame
		return CFrame.new(cx + x, FLOOR_TOP + y, z)
	end
	local W, D, H = ROOM_W, ROOM_D, ROOM_H
	local back = -D / 2 - WALL / 2

	part(room, "Floor", Vector3.new(W, 1, D), at(0, -0.5, 0), floorColor, floorMaterial)
	part(room, "Ceiling", Vector3.new(W + 2 * WALL, 1, D + WALL), at(0, H + 0.5, -WALL / 2), WHITE)

	-- Back wall with a 7 x 5 window (sill at y = 4), built around the opening.
	local wl, wr = winX - 3.5, winX + 3.5
	part(room, "BackWallLeft", Vector3.new(wl + W / 2, H, WALL), at((-W / 2 + wl) / 2, H / 2, back), wallColor)
	part(room, "BackWallRight", Vector3.new(W / 2 - wr, H, WALL), at((wr + W / 2) / 2, H / 2, back), wallColor)
	part(room, "BackWallBelow", Vector3.new(7, 4, WALL), at(winX, 2, back), wallColor)
	part(room, "BackWallAbove", Vector3.new(7, H - 9, WALL), at(winX, (9 + H) / 2, back), wallColor)
	local glass = part(room, "WindowGlass", Vector3.new(7, 5, 0.2), at(winX, 6.5, back), Color3.fromRGB(190, 225, 255), Enum.Material.Glass)
	glass.Transparency = 0.6
	part(room, "SillBottom", Vector3.new(7.6, 0.3, 1.4), at(winX, 4, back + 0.3), WHITE)
	part(room, "FrameTop", Vector3.new(7.6, 0.3, 1.2), at(winX, 9, back + 0.2), WHITE)
	part(room, "FrameLeft", Vector3.new(0.3, 5, 1.2), at(wl, 6.5, back + 0.2), WHITE)
	part(room, "FrameRight", Vector3.new(0.3, 5, 1.2), at(wr, 6.5, back + 0.2), WHITE)
	part(room, "SkyOutside", Vector3.new(12, 9, 0.5), at(winX, 6.5, back - 3), Color3.fromRGB(150, 200, 240))

	-- Left wall, solid. Right wall with a door (4.5 wide, 8 high) towards the back.
	part(room, "LeftWall", Vector3.new(WALL, H, D), at(-W / 2 - WALL / 2, H / 2, 0), wallColor)
	local doorZ = -3
	local dz1, dz2 = doorZ - 2.25, doorZ + 2.25
	local rx = W / 2 + WALL / 2
	part(room, "RightWallBack", Vector3.new(WALL, H, dz1 + D / 2), at(rx, H / 2, (-D / 2 + dz1) / 2), wallColor)
	part(room, "RightWallFront", Vector3.new(WALL, H, D / 2 - dz2), at(rx, H / 2, (dz2 + D / 2) / 2), wallColor)
	part(room, "RightWallAbove", Vector3.new(WALL, H - 8, 4.5), at(rx, (8 + H) / 2, doorZ), wallColor)
	part(room, "Door", Vector3.new(0.4, 8, 4.5), at(rx, 4, doorZ), WOOD, Enum.Material.Wood)
	part(room, "DoorKnob", Vector3.new(0.4, 0.4, 0.4), at(rx - 0.4, 3.8, doorZ + 1.6), Color3.fromRGB(210, 180, 90), Enum.Material.Metal, Enum.PartType.Ball)

	-- Skirting boards
	part(room, "SkirtBack", Vector3.new(W, 0.6, 0.3), at(0, 0.3, -D / 2 + 0.15), WHITE)
	part(room, "SkirtLeft", Vector3.new(0.3, 0.6, D), at(-W / 2 + 0.15, 0.3, 0), WHITE)

	-- Lights: a ceiling lamp plus a soft fill near the open front so faces read on camera.
	local lamp = part(room, "CeilingLamp", Vector3.new(2.4, 0.3, 2.4), at(0, H - 0.15, -2), Color3.fromRGB(255, 240, 210), Enum.Material.Neon)
	light(lamp, 1.6, 30)
	local fill = part(room, "FrontFill", Vector3.new(1, 1, 1), at(0, H - 1.5, D / 2 - 1), WHITE)
	fill.Transparency = 1
	fill.CanCollide = false
	light(fill, 0.8, 24, Color3.fromRGB(235, 240, 255))

	-- Cameras: a wide from in front of the open side, and a closer one.
	local key = name:gsub("Room", "")
	marker(`Cam_{key}_Wide`, at(0, 6, D / 2 + 14).Position, at(0, 3.5, -3).Position)
	marker(`Cam_{key}_Close`, at(0, 5, D / 2 + 3).Position, at(0, 3.5, -4).Position)
	return room, at, key
end

-- Bedroom: bed, nightstand + lamp, wardrobe, desk under the window, chair, rug, poster.
do
	local room, at, key = makeRoom("Bedroom", 300, Color3.fromRGB(180, 205, 235), Color3.fromRGB(160, 115, 80), Enum.Material.WoodPlanks, 1.5)
	local bed = Instance.new("Model")
	bed.Name = "Bed"
	bed.Parent = room
	part(bed, "Frame", Vector3.new(6, 1.4, 9), at(-6, 0.7, -4.5), WOOD, Enum.Material.Wood)
	part(bed, "Headboard", Vector3.new(6.4, 4, 0.6), at(-6, 2, -8.7), WOOD, Enum.Material.Wood)
	part(bed, "Mattress", Vector3.new(5.6, 0.7, 8.4), at(-6, 1.75, -4.6), WHITE, Enum.Material.Fabric)
	part(bed, "Pillow", Vector3.new(4, 0.6, 1.6), at(-6, 2.4, -7.6), Color3.fromRGB(255, 255, 255), Enum.Material.Fabric)
	part(bed, "Blanket", Vector3.new(5.8, 0.3, 5.2), at(-6, 2.2, -2.6), Color3.fromRGB(240, 150, 90), Enum.Material.Fabric)

	part(room, "Nightstand", Vector3.new(2.2, 2.4, 2), at(-10.4, 1.2, -7.6), WOOD, Enum.Material.Wood)
	part(room, "LampBase", Vector3.new(0.6, 1.2, 0.6), at(-10.4, 3, -7.6), DARK, Enum.Material.Metal)
	local shade = part(room, "LampShade", Vector3.new(1.4, 1, 1.4), at(-10.4, 4.1, -7.6), Color3.fromRGB(255, 230, 180), Enum.Material.Neon)
	light(shade, 0.8, 10)

	part(room, "Wardrobe", Vector3.new(5, 9, 2.4), at(8.8, 4.5, -7.6), Color3.fromRGB(235, 225, 205), Enum.Material.Wood)
	part(room, "WardrobeSplit", Vector3.new(0.1, 8.4, 0.1), at(8.8, 4.5, -6.35), DARK)

	table4(room, "Desk", at(1.5, 0, -7.3), 5, 2.6, 3.2, Color3.fromRGB(235, 225, 205))
	part(room, "Laptop", Vector3.new(1.8, 0.1, 1.3), at(1.5, 3.25, -7.3), DARK, Enum.Material.Metal)
	chair(room, at(1.5, 0, -4.8), Color3.fromRGB(90, 140, 200)) -- faces the desk
	part(room, "Rug", Vector3.new(7, 0.1, 5), at(1.5, 0.05, 0.5), Color3.fromRGB(120, 170, 140), Enum.Material.Fabric)
	part(room, "Poster", Vector3.new(0.2, 4, 3), at(-11.85, 6.5, 0), Color3.fromRGB(255, 200, 60))

	marker(`Mark_{key}_Bed`, at(-6, 2.1, -4.5).Position)
	marker(`Mark_{key}_Desk`, at(1.5, 0, -3.8).Position)
	marker(`Mark_{key}_Center`, at(1, 0, 2).Position)
end

-- Kitchen: counter run with sink and hob, oven, fridge, wall cabinets, table and four chairs, pendant lamp.
do
	local room, at, key = makeRoom("Kitchen", 340, Color3.fromRGB(240, 225, 190), Color3.fromRGB(215, 215, 210), Enum.Material.Marble, -1)
	part(room, "BaseCabinets", Vector3.new(15, 3.4, 2.6), at(-3.5, 1.7, -7.7), WHITE, Enum.Material.Wood)
	part(room, "Worktop", Vector3.new(15.4, 0.4, 3), at(-3.5, 3.6, -7.6), Color3.fromRGB(70, 72, 78), Enum.Material.Granite)
	part(room, "Sink", Vector3.new(2.6, 0.1, 1.8), at(-1, 3.82, -7.6), Color3.fromRGB(170, 175, 180), Enum.Material.Metal)
	part(room, "Tap", Vector3.new(0.25, 1.2, 0.25), at(-1, 4.4, -8.5), Color3.fromRGB(190, 195, 200), Enum.Material.Metal)
	for _, o in { Vector3.new(-0.7, 0, -0.6), Vector3.new(0.7, 0, -0.6), Vector3.new(-0.7, 0, 0.6), Vector3.new(0.7, 0, 0.6) } do
		part(room, "Burner", Vector3.new(0.1, 1, 1), at(-8 + o.X, 3.85, -7.6 + o.Z) * CFrame.Angles(0, 0, math.pi / 2), DARK, Enum.Material.Metal, Enum.PartType.Cylinder)
	end
	part(room, "OvenDoor", Vector3.new(2.6, 1.8, 0.1), at(-8, 1.6, -6.35), Color3.fromRGB(30, 30, 35), Enum.Material.Glass)
	part(room, "WallCabinets", Vector3.new(6, 3, 1.6), at(-8, 8.5, -8.2), WHITE, Enum.Material.Wood)
	part(room, "Fridge", Vector3.new(3.4, 8, 3), at(8, 4, -7.4), Color3.fromRGB(205, 210, 215), Enum.Material.Metal)
	part(room, "FridgeHandle", Vector3.new(0.2, 2.5, 0.2), at(6.6, 5, -5.8), DARK, Enum.Material.Metal)

	table4(room, "Table", at(2, 0, 2), 6, 4, 3.2, WOOD)
	-- {x, z, yaw}: each chair faces the table (a chair looks along its CFrame's -Z)
	for _, c in { { -2.3, 2, -math.pi / 2 }, { 6.3, 2, math.pi / 2 }, { 2, -1.3, math.pi }, { 2, 5.3, 0 } } do
		chair(room, at(c[1], 0, c[2]) * CFrame.Angles(0, c[3], 0), Color3.fromRGB(200, 90, 70))
	end
	part(room, "FruitBowl", Vector3.new(0.6, 1.6, 1.6), at(2, 3.5, 2) * CFrame.Angles(0, 0, math.pi / 2), Color3.fromRGB(240, 240, 240), Enum.Material.SmoothPlastic, Enum.PartType.Cylinder)
	part(room, "Apple", Vector3.new(0.6, 0.6, 0.6), at(1.8, 3.95, 2.1), Color3.fromRGB(210, 40, 40), Enum.Material.SmoothPlastic, Enum.PartType.Ball)
	part(room, "Orange", Vector3.new(0.6, 0.6, 0.6), at(2.3, 3.95, 1.8), Color3.fromRGB(245, 150, 30), Enum.Material.SmoothPlastic, Enum.PartType.Ball)
	part(room, "PendantCord", Vector3.new(0.1, 3, 0.1), at(2, 10.5, 2), DARK)
	local pendant = part(room, "PendantShade", Vector3.new(1.8, 0.8, 1.8), at(2, 8.6, 2), Color3.fromRGB(255, 235, 200), Enum.Material.Neon)
	light(pendant, 1, 14)

	marker(`Mark_{key}_Sink`, at(-1, 0, -5.4).Position)
	marker(`Mark_{key}_Hob`, at(-8, 0, -5.4).Position)
	marker(`Mark_{key}_Table`, at(2, 0, 6.2).Position)
	marker(`Mark_{key}_Center`, at(-3, 0, 4).Position)
end

-- Living room: TV on the left wall, sofa on the right facing it (both read in profile from the
-- front camera), coffee table, rug, bookshelf, floor lamp, plant.
do
	local room, at, key = makeRoom("LivingRoom", 380, Color3.fromRGB(190, 215, 190), Color3.fromRGB(185, 140, 95), Enum.Material.WoodPlanks, 6)
	part(room, "TVStand", Vector3.new(2, 2.4, 7), at(-10.8, 1.2, -1), WOOD, Enum.Material.Wood)
	part(room, "TV", Vector3.new(0.4, 4.2, 7), at(-10.9, 5, -1), DARK)
	part(room, "TVScreen", Vector3.new(0.1, 3.8, 6.6), at(-10.65, 5, -1), Color3.fromRGB(20, 30, 45), Enum.Material.Glass) -- add a SurfaceGui (Face = Right) to show a picture

	local sofa = Instance.new("Model")
	sofa.Name = "Sofa"
	sofa.Parent = room
	local sofaColor = Color3.fromRGB(200, 110, 90)
	part(sofa, "Base", Vector3.new(3.2, 1.6, 8), at(6, 0.8, -1), sofaColor, Enum.Material.Fabric)
	part(sofa, "Back", Vector3.new(1, 3.4, 8), at(8.1, 1.9, -1), sofaColor, Enum.Material.Fabric)
	part(sofa, "ArmBack", Vector3.new(4.2, 2.4, 1), at(6.5, 1.2, -5.5), sofaColor, Enum.Material.Fabric)
	part(sofa, "ArmFront", Vector3.new(4.2, 2.4, 1), at(6.5, 1.2, 3.5), sofaColor, Enum.Material.Fabric)
	part(sofa, "CushionA", Vector3.new(2.8, 0.6, 3.8), at(5.9, 1.9, -3), Color3.fromRGB(215, 130, 110), Enum.Material.Fabric)
	part(sofa, "CushionB", Vector3.new(2.8, 0.6, 3.8), at(5.9, 1.9, 1), Color3.fromRGB(215, 130, 110), Enum.Material.Fabric)

	table4(room, "CoffeeTable", at(0.5, 0, -1), 3, 4.5, 1.6, WOOD)
	part(room, "Rug", Vector3.new(14, 0.1, 9), at(-1, 0.05, -1), Color3.fromRGB(220, 200, 150), Enum.Material.Fabric)

	part(room, "Bookshelf", Vector3.new(6, 9, 1.6), at(-4, 4.5, -8.2), WOOD, Enum.Material.Wood)
	local bookColors = { Color3.fromRGB(200, 60, 60), Color3.fromRGB(60, 120, 200), Color3.fromRGB(240, 190, 60), Color3.fromRGB(90, 170, 100), Color3.fromRGB(150, 90, 180) }
	for row = 0, 2 do
		for i = 0, 4 do
			part(room, "Book", Vector3.new(0.7, 1.8, 1.2), at(-6.2 + i * 1.1, 1.5 + row * 2.9, -7.4), bookColors[((i + row) % #bookColors) + 1])
		end
	end
	part(room, "LampPole", Vector3.new(0.3, 6, 0.3), at(10.5, 3, -7.5), DARK, Enum.Material.Metal)
	local fl = part(room, "LampShade", Vector3.new(1.6, 1.2, 1.6), at(10.5, 6.5, -7.5), Color3.fromRGB(255, 235, 200), Enum.Material.Neon)
	light(fl, 0.9, 12)
	part(room, "PlantPot", Vector3.new(1.6, 1.6, 1.6), at(-10.5, 0.8, -7.5) * CFrame.Angles(0, 0, math.pi / 2), Color3.fromRGB(190, 110, 70), Enum.Material.SmoothPlastic, Enum.PartType.Cylinder)
	part(room, "Plant", Vector3.new(2.8, 2.8, 2.8), at(-10.5, 2.8, -7.5), Color3.fromRGB(80, 150, 70), Enum.Material.Grass, Enum.PartType.Ball)

	marker(`Mark_{key}_Sofa`, at(5.9, 2.2, -1).Position)
	marker(`Mark_{key}_TV`, at(-6, 0, 3).Position)
	marker(`Mark_{key}_Center`, at(-2, 0, 4).Position)
end

-- A plain stage floor under the Backlot so the rooms don't float in the void.
local stage = backlot:FindFirstChild("BacklotFloor")
if stage then
	stage:Destroy()
end
local slab = part(backlot, "BacklotFloor", Vector3.new(130, 1, 70), CFrame.new(340, -0.45, 5), Color3.fromRGB(95, 95, 100), Enum.Material.Concrete)
slab.Name = "BacklotFloor"

local count = #home:GetDescendants()
return `Home room kit built: Bedroom (x=300), Kitchen (x=340), LivingRoom (x=380); {count} instances.`
