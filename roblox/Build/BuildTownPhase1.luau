-- BuildTownPhase1
-- Phase 1 of town-plan.md: streets, sidewalks, street lamps, a bigger ground, and the exterior
-- shells of every building, so the town reads as a real place from any angle. The square stays
-- where it is and becomes enclosed: shops east, apartments + library west, Town Hall row south,
-- bakery street north (from BuildEP01Map). School, Hero's house, park and arena sit in the outer ring.
-- Run in Edit mode after BuildEP01Map. Safe to re-run (rebuilds workspace.Town).
--
-- Buildings are hollow shells: real walls with window and door openings, a floor slab per storey
-- and a roof, so interiors can be added in phase 2. The street-facing wall of each building is a
-- Model named "FrontWall" with the attribute Cutaway = true; shot scripts hide it to film inside.

local GROUND = 0.55 -- road / plaza top
local STOREY = 12

local town = workspace:FindFirstChild("Town")
if town then
	town:Destroy()
end
town = Instance.new("Folder")
town.Name = "Town"
town.Parent = workspace

local function folder(name: string): Folder
	local f = Instance.new("Folder")
	f.Name = name
	f.Parent = town
	return f
end

local ASPHALT = Color3.fromRGB(70, 72, 80)
local PAVEMENT = Color3.fromRGB(170, 170, 165)
local GLASS = Color3.fromRGB(170, 210, 235)
local DOOR = Color3.fromRGB(110, 70, 45)
local TRIM = Color3.fromRGB(240, 238, 232)
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

local function signText(board: BasePart, text: string, color: Color3)
	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Front
	gui.PixelsPerStud = 40
	gui.Parent = board
	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Text = text
	label.TextScaled = true
	label.FontFace = Font.fromEnum(Enum.Font.GothamBlack)
	label.TextColor3 = color
	label.Parent = gui
end

-- A wall with rectangular openings, built from solid pieces around them.
-- `bottom` is the CFrame at the wall's bottom centre (local X runs along the wall).
-- Each opening is { x0, x1, y0, y1, kind } in wall space, kind = "window" | "door" | "store" | "open".
local function wallWithOpenings(parent: Instance, bottom: CFrame, width: number, height: number, color: Color3, material: Enum.Material, openings: { any })
	local xs = { -width / 2, width / 2 }
	for _, o in openings do
		table.insert(xs, math.clamp(o[1], -width / 2, width / 2))
		table.insert(xs, math.clamp(o[2], -width / 2, width / 2))
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
		local holes = {}
		for _, o in openings do
			if o[1] <= a + 1e-3 and o[2] >= b - 1e-3 then
				table.insert(holes, { o[3], o[4] })
			end
		end
		table.sort(holes, function(p, q)
			return p[1] < q[1]
		end)
		local y = 0
		local function fill(y0: number, y1: number)
			if y1 - y0 > 1e-3 then
				part(parent, "Wall", Vector3.new(b - a, y1 - y0, 1), bottom * CFrame.new((a + b) / 2, (y0 + y1) / 2, 0), color, material)
			end
		end
		for _, h in holes do
			fill(y, h[1])
			y = math.max(y, h[2])
		end
		fill(y, height)
	end
	-- Fill the openings: glass for windows and shop fronts, a door panel for doors.
	for _, o in openings do
		local w, h = o[2] - o[1], o[4] - o[3]
		local cf = bottom * CFrame.new((o[1] + o[2]) / 2, (o[3] + o[4]) / 2, 0)
		if o[5] == "window" or o[5] == "store" then
			local g = part(parent, "Glass", Vector3.new(w, h, 0.2), cf, GLASS, Enum.Material.Glass)
			g.Transparency = 0.55
			part(parent, "Sill", Vector3.new(w + 0.6, 0.3, 1.4), bottom * CFrame.new((o[1] + o[2]) / 2, o[3], 0), TRIM)
		elseif o[5] == "door" then
			part(parent, "Door", Vector3.new(w, h, 0.4), cf, DOOR, Enum.Material.Wood)
		end
	end
end

-- Evenly spaced windows on one storey of a wall.
local function windowRow(list: { any }, wallWidth: number, storeyBase: number, avoidHalfWidth: number?)
	local n = math.max(1, math.floor(wallWidth / 8))
	local spacing = wallWidth / n
	for i = 1, n do
		local cx = -wallWidth / 2 + spacing * (i - 0.5)
		if not (avoidHalfWidth and math.abs(cx) < avoidHalfWidth + 2.5) then
			table.insert(list, { cx - 2, cx + 2, storeyBase + 4, storeyBase + 8.5, "window" })
		end
	end
end

-- One building shell. The front faces `front` (a unit vector pointing at the street).
type Spec = {
	name: string, x: number, z: number, front: Vector3, W: number, D: number, floors: number,
	storeyH: number?, color: Color3, material: Enum.Material?, roof: Color3?,
	storefront: boolean?, doorW: number?, doorH: number?,
	sign: string?, signColor: Color3?, signBoard: Color3?, awning: Color3?,
}
local function building(parent: Instance, s: Spec): (Model, (number, number, number) -> CFrame, number)
	local m = Instance.new("Model")
	m.Name = s.name
	local sh = s.storeyH or STOREY
	local H = s.floors * sh + 2.5
	local origin = Vector3.new(s.x, GROUND, s.z)
	local base = CFrame.lookAt(origin, origin + s.front)
	local function L(x: number, y: number, z: number): CFrame
		return base * CFrame.new(x, y, z)
	end
	local W, D = s.W, s.D
	local mat = s.material or Enum.Material.Brick
	local doorW, doorH = s.doorW or 5, s.doorH or 8

	-- Front wall (cutaway)
	local frontWall = Instance.new("Model")
	frontWall.Name = "FrontWall"
	frontWall:SetAttribute("Cutaway", true)
	frontWall.Parent = m
	local fo = {}
	if s.storefront then
		table.insert(fo, { -W / 2 + 2.5, -doorW / 2, 0.8, 8.5, "store" })
		table.insert(fo, { doorW / 2, W / 2 - 2.5, 0.8, 8.5, "store" })
		table.insert(fo, { -doorW / 2, doorW / 2, 0, doorH, "door" })
	else
		table.insert(fo, { -doorW / 2, doorW / 2, 0, doorH, "door" })
		windowRow(fo, W - 2, 0, doorW / 2)
	end
	for f = 2, s.floors do
		windowRow(fo, W - 2, (f - 1) * sh)
	end
	wallWithOpenings(frontWall, L(0, 0, -D / 2 + 0.5), W, H, s.color, mat, fo)

	-- Back and side walls
	local walls = Instance.new("Model")
	walls.Name = "Walls"
	walls.Parent = m
	local bo, so = {}, {}
	for f = 1, s.floors do
		windowRow(bo, W - 2, (f - 1) * sh)
		windowRow(so, D - 4, (f - 1) * sh)
	end
	wallWithOpenings(walls, L(0, 0, D / 2 - 0.5) * CFrame.Angles(0, math.pi, 0), W, H, s.color, mat, bo)
	wallWithOpenings(walls, L(-W / 2 + 0.5, 0, 0) * CFrame.Angles(0, math.pi / 2, 0), D - 2, H, s.color, mat, so)
	wallWithOpenings(walls, L(W / 2 - 0.5, 0, 0) * CFrame.Angles(0, -math.pi / 2, 0), D - 2, H, s.color, mat, so)

	-- Floor slabs per storey, roof
	for f = 1, s.floors do
		part(m, `Floor{f}`, Vector3.new(W - 2, 0.7, D - 2), L(0, (f - 1) * sh, 0), Color3.fromRGB(180, 170, 155), Enum.Material.WoodPlanks)
	end
	part(m, "Roof", Vector3.new(W - 2, 0.7, D - 2), L(0, s.floors * sh, 0), s.roof or Color3.fromRGB(85, 80, 80), Enum.Material.Slate)
	part(m, "Coping", Vector3.new(W + 0.6, 0.5, 0.8), L(0, H + 0.25, -D / 2 + 0.4), TRIM)

	-- Sign and awning
	if s.sign then
		local y = if s.storefront then 9.9 else doorH + 1.6
		local board = part(m, "Sign", Vector3.new(math.min(W - 3, 20), 2.4, 0.4), L(0, y, -D / 2 - 0.25), s.signBoard or DARK, Enum.Material.SmoothPlastic)
		signText(board, s.sign, s.signColor or Color3.fromRGB(255, 240, 210))
	end
	if s.awning then
		part(m, "Awning", Vector3.new(W - 3, 0.4, 3.4), L(0, 8.9, -D / 2 - 1.7) * CFrame.Angles(math.rad(10), 0, 0), s.awning, Enum.Material.Fabric)
	end
	-- Doorstep
	part(m, "Step", Vector3.new(doorW + 2, 0.35, 2), L(0, 0.17, -D / 2 - 1), PAVEMENT, Enum.Material.Concrete)

	m:SetAttribute("Storeys", s.floors)
	m:SetAttribute("StoreyHeight", sh)
	m.Parent = parent
	return m, L, H
end

-- Ground: grow the EP01 grass so the outer ring has somewhere to stand.
local grass = workspace:FindFirstChild("EP01_Map") and workspace.EP01_Map:FindFirstChild("Ground") and workspace.EP01_Map.Ground:FindFirstChild("Grass")
if grass then
	grass.Size = Vector3.new(520, 1, 520)
	grass.CFrame = CFrame.new(0, -0.45, 40)
end

-- Streets
local streets = folder("Streets")
local function road(name: string, cx: number, cz: number, sx: number, sz: number)
	part(streets, name, Vector3.new(sx, 1, sz), CFrame.new(cx, 0.05, cz), ASPHALT, Enum.Material.Asphalt)
end
local function walk(name: string, cx: number, cz: number, sx: number, sz: number)
	part(streets, name, Vector3.new(sx, 1.4, sz), CFrame.new(cx, 0.2, cz), PAVEMENT, Enum.Material.Concrete)
end
road("RingWest", -54, 2, 12, 104)
road("RingEast", 54, 2, 12, 104)
road("SquareRoadSouth", 0, 54, 212, 12)
road("SchoolRoad", 0, 100, 300, 12)
road("AvenueWest", -100, 21.5, 12, 169)
road("AvenueEast", 100, 21.5, 12, 169)
walk("WalkSquareNorth", 0, -48, 90, 4)
walk("WalkSquareWest", -46.5, 2, 3, 94)
walk("WalkSquareEast", 46.5, 2, 3, 94)
walk("WalkSquareSouth", 0, 46.5, 90, 3)
walk("WalkWestShops", -61.5, 2, 3, 104)
walk("WalkEastShops", 61.5, 2, 3, 104)
-- Sidewalks stop at crossings so no curb runs across a road.
walk("WalkSouthRow", 0, 61.5, 182, 3)
for _, z in { 92.5, 107.5 } do
	walk("WalkSchool", -122, z, 32, 3)
	walk("WalkSchool", 0, z, 188, 3)
	walk("WalkSchool", 122, z, 32, 3)
end
for _, x in { -107.5, -92.5, 92.5, 107.5 } do
	walk("WalkAvenue", x, -1, 3, 98) -- Bakery Road to Square Road South
	walk("WalkAvenue", x, 77, 3, 34) -- Square Road South to School Road
end
task.wait()

-- Street lamps (lit; they read as decoration by day and light the streets at night)
local lamps = folder("Lamps")
local function lamp(pos: Vector3)
	local m = Instance.new("Model")
	m.Name = "Lamp"
	part(m, "Pole", Vector3.new(0.5, 10, 0.5), CFrame.new(pos + Vector3.new(0, 5.9, 0)), DARK, Enum.Material.Metal)
	local head = part(m, "Head", Vector3.new(1.4, 0.7, 1.4), CFrame.new(pos + Vector3.new(0, 11.2, 0)), Color3.fromRGB(255, 230, 180), Enum.Material.Neon)
	local l = Instance.new("PointLight")
	l.Brightness = 0.7
	l.Range = 20
	l.Color = Color3.fromRGB(255, 215, 160)
	l.Parent = head
	m.Parent = lamps
end
for z = -40, 40, 20 do
	lamp(Vector3.new(-61.5, 0.9, z))
	lamp(Vector3.new(61.5, 0.9, z))
end
for x = -40, 40, 20 do
	lamp(Vector3.new(x, 0.9, 61.5))
end
for x = -140, 140, 35 do
	lamp(Vector3.new(x, 0.9, 92.5))
end
for z = -30, 80, 22 do
	lamp(Vector3.new(-92.5, 0.9, z))
	lamp(Vector3.new(92.5, 0.9, z))
end
task.wait()

local buildings = folder("Buildings")

-- East side of the square: Market Street shops, facing west onto the square.
local shopSpecs = {
	{ "SneakerShop", -36, "SNEAKERS", Color3.fromRGB(235, 120, 90), Color3.fromRGB(240, 90, 70) },
	{ "Cafe", -18, "CAFE", Color3.fromRGB(150, 200, 170), Color3.fromRGB(70, 140, 100) },
	{ "CornerShop", 0, "CORNER SHOP", Color3.fromRGB(240, 210, 130), Color3.fromRGB(60, 110, 190) },
	{ "Restaurant", 18, "PIZZA", Color3.fromRGB(230, 150, 150), Color3.fromRGB(200, 50, 50) },
	{ "Laundromat", 36, "LAUNDRY", Color3.fromRGB(170, 200, 235), Color3.fromRGB(90, 150, 220) },
}
for _, s in shopSpecs do
	building(buildings, {
		name = s[1], x = 73, z = s[2], front = -Vector3.xAxis, W = 17.5, D = 20, floors = 2,
		color = s[4], storefront = true, sign = s[3], awning = s[5],
	})
	task.wait()
end

-- West side: apartment block and library, facing east onto the square.
building(buildings, {
	name = "ApartmentBlock", x = -73, z = -20, front = Vector3.xAxis, W = 50, D = 20, floors = 3,
	color = Color3.fromRGB(205, 175, 150), doorW = 6, doorH = 9, sign = "MAPLE COURT", signBoard = Color3.fromRGB(60, 60, 70),
})
task.wait()
building(buildings, {
	name = "Library", x = -73, z = 27, front = Vector3.xAxis, W = 36, D = 20, floors = 2, storeyH = 13,
	color = Color3.fromRGB(190, 200, 215), material = Enum.Material.Concrete, doorW = 6, doorH = 9, sign = "LIBRARY",
	signBoard = Color3.fromRGB(40, 60, 100),
})
task.wait()

-- South side: toy shop, Town Hall with clock tower, music shop, facing north onto the square.
building(buildings, {
	name = "ToyShop", x = -34, z = 73, front = -Vector3.zAxis, W = 22, D = 20, floors = 2,
	color = Color3.fromRGB(250, 200, 110), storefront = true, sign = "TOYS", awning = Color3.fromRGB(240, 110, 160),
})
task.wait()
building(buildings, {
	name = "MusicShop", x = 34, z = 73, front = -Vector3.zAxis, W = 22, D = 20, floors = 2,
	color = Color3.fromRGB(160, 140, 200), storefront = true, sign = "MUSIC", awning = Color3.fromRGB(110, 80, 170),
})
task.wait()
do
	local hall, L, H = building(buildings, {
		name = "TownHall", x = 0, z = 75, front = -Vector3.zAxis, W = 40, D = 24, floors = 2, storeyH = 13,
		color = Color3.fromRGB(225, 215, 195), material = Enum.Material.Concrete, doorW = 7, doorH = 10,
		sign = "TOWN HALL", signBoard = Color3.fromRGB(120, 40, 40),
	})
	-- Clock tower on the roof, set back from the front edge.
	local tower = Instance.new("Model")
	tower.Name = "ClockTower"
	tower.Parent = hall
	part(tower, "Tower", Vector3.new(10, 20, 10), L(0, H + 10, -4), Color3.fromRGB(215, 205, 185), Enum.Material.Concrete)
	part(tower, "Cap", Vector3.new(12, 1.5, 12), L(0, H + 20.75, -4), Color3.fromRGB(120, 40, 40), Enum.Material.Slate)
	part(tower, "Spire", Vector3.new(6, 4, 6), L(0, H + 23.5, -4), Color3.fromRGB(120, 40, 40), Enum.Material.Slate)
	part(tower, "ClockFace", Vector3.new(0.4, 7, 7), L(0, H + 13, -9.2) * CFrame.Angles(0, math.pi / 2, 0), Color3.fromRGB(250, 248, 235), Enum.Material.SmoothPlastic, Enum.PartType.Cylinder)
	part(tower, "HourHand", Vector3.new(0.4, 2.2, 0.2), L(0, H + 13.9, -9.5), DARK)
	part(tower, "MinuteHand", Vector3.new(0.3, 3.2, 0.2), L(0.9, H + 13, -9.5) * CFrame.Angles(0, 0, math.rad(-70)), DARK)
	-- Front columns
	for _, x in { -6, 6 } do
		-- a cylinder's length runs along its X axis, so size X is the column height, turned upright
		part(hall, "Column", Vector3.new(11, 1.4, 1.4), L(x, 5.5, -13.2) * CFrame.Angles(0, 0, math.pi / 2), TRIM, Enum.Material.Marble, Enum.PartType.Cylinder)
	end
	part(hall, "Portico", Vector3.new(16, 1, 4), L(0, 11.3, -13.4), TRIM, Enum.Material.Marble)
end
task.wait()

-- Outer ring: school (south), Hero's house + garage (south-east), arena (east), park (south-west).
do
	local school, L = building(buildings, {
		name = "School", x = 0, z = 155, front = -Vector3.zAxis, W = 80, D = 30, floors = 2,
		color = Color3.fromRGB(225, 140, 95), doorW = 8, doorH = 9, sign = "SCHOOL", signBoard = Color3.fromRGB(40, 70, 120),
	})
	local yard = Instance.new("Model")
	yard.Name = "Schoolyard"
	yard.Parent = school
	part(yard, "Yard", Vector3.new(80, 0.4, 30), CFrame.new(0, 0.6, 124), Color3.fromRGB(150, 150, 155), Enum.Material.Concrete)
	part(yard, "Court", Vector3.new(40, 0.1, 22), CFrame.new(0, 0.85, 124), Color3.fromRGB(60, 120, 180), Enum.Material.SmoothPlastic)
	part(yard, "CentreLine", Vector3.new(0.3, 0.05, 22), CFrame.new(0, 0.92, 124), Color3.new(1, 1, 1))
	for _, x in { -19, 19 } do
		part(yard, "HoopPole", Vector3.new(0.5, 9, 0.5), CFrame.new(x + (if x < 0 then -1.5 else 1.5), 5, 124), DARK, Enum.Material.Metal)
		part(yard, "Backboard", Vector3.new(0.3, 3, 4.5), CFrame.new(x, 9, 124), Color3.new(1, 1, 1))
		part(yard, "Hoop", Vector3.new(0.2, 1.6, 1.6), CFrame.new(x + (if x < 0 then 1 else -1), 8, 124) * CFrame.Angles(0, 0, math.pi / 2), Color3.fromRGB(230, 90, 30), Enum.Material.Metal, Enum.PartType.Cylinder)
	end
	for x = -40, 40, 4 do
		if math.abs(x) > 5 then
			part(yard, "FencePost", Vector3.new(0.3, 4, 0.3), CFrame.new(x, 2.6, 110), DARK, Enum.Material.Metal)
		end
	end
	part(yard, "FenceRailWest", Vector3.new(35, 0.3, 0.2), CFrame.new(-22.5, 4.2, 110), DARK, Enum.Material.Metal)
	part(yard, "FenceRailEast", Vector3.new(35, 0.3, 0.2), CFrame.new(22.5, 4.2, 110), DARK, Enum.Material.Metal)
	part(yard, "Flagpole", Vector3.new(0.4, 16, 0.4), CFrame.new(28, 8.6, 136), Color3.fromRGB(200, 200, 205), Enum.Material.Metal)
	part(yard, "Flag", Vector3.new(4, 2.6, 0.1), CFrame.new(30.2, 15, 136), Color3.fromRGB(230, 70, 60), Enum.Material.Fabric)
	local _ = L
end
task.wait()

do
	building(buildings, {
		name = "HeroHouse", x = 122, z = 127, front = -Vector3.zAxis, W = 24, D = 22, floors = 2,
		color = Color3.fromRGB(200, 215, 235), material = Enum.Material.WoodPlanks, doorW = 4.5, doorH = 8,
		roof = Color3.fromRGB(110, 60, 55),
	})
	local garage, GL = building(buildings, {
		name = "Garage", x = 142.5, z = 129, front = -Vector3.zAxis, W = 13, D = 18, floors = 1, storeyH = 10,
		color = Color3.fromRGB(200, 215, 235), material = Enum.Material.WoodPlanks, doorW = 9, doorH = 7.5,
	})
	local gd = garage.FrontWall:FindFirstChild("Door")
	if gd then
		gd.Name = "GarageDoor"
		gd.Color = Color3.fromRGB(225, 225, 225)
		gd.Material = Enum.Material.DiamondPlate
	end
	local garden = Instance.new("Model")
	garden.Name = "Garden"
	garden.Parent = buildings.HeroHouse
	for x = 108, 150, 3 do
		if math.abs(x - 122) > 2 and math.abs(x - 142.5) > 5 then
			part(garden, "Picket", Vector3.new(0.4, 2.6, 0.4), CFrame.new(x, 1.9, 112.5), Color3.new(1, 1, 1), Enum.Material.Wood)
		end
	end
	part(garden, "Path", Vector3.new(3, 0.2, 3.5), CFrame.new(122, 0.65, 114.3), PAVEMENT, Enum.Material.Concrete)
	part(garden, "Drive", Vector3.new(9, 0.2, 9), CFrame.new(142.5, 0.65, 115), PAVEMENT, Enum.Material.Concrete)
	part(garden, "MailboxPost", Vector3.new(0.4, 3.4, 0.4), CFrame.new(118.5, 2.2, 112), DARK)
	part(garden, "Mailbox", Vector3.new(1.4, 1, 0.9), CFrame.new(118.5, 4, 112), Color3.fromRGB(60, 110, 190), Enum.Material.Metal)
	local _ = GL
end
task.wait()

do
	local arena, L = building(buildings, {
		name = "Arena", x = 145, z = -10, front = -Vector3.xAxis, W = 60, D = 50, floors = 1, storeyH = 20,
		color = Color3.fromRGB(120, 130, 165), material = Enum.Material.Concrete, doorW = 10, doorH = 10,
		sign = "ARENA", signBoard = Color3.fromRGB(200, 50, 60),
	})
	part(arena, "Marquee", Vector3.new(30, 4, 0.6), L(0, 17, -25.4), Color3.fromRGB(30, 30, 40)).Name = "Marquee"
	signText(arena.Marquee, "FRIDAY NIGHT RUMBLE", Color3.fromRGB(255, 210, 74))
end
task.wait()

do
	local park = Instance.new("Model")
	park.Name = "Park"
	park.Parent = buildings
	part(park, "PathNS", Vector3.new(4, 0.2, 60), CFrame.new(-128, 0.65, 140), Color3.fromRGB(200, 185, 150), Enum.Material.Sand)
	part(park, "PathEW", Vector3.new(36, 0.2, 4), CFrame.new(-128, 0.65, 135), Color3.fromRGB(200, 185, 150), Enum.Material.Sand)
	part(park, "Pond", Vector3.new(0.3, 16, 16), CFrame.new(-138, 0.6, 160) * CFrame.Angles(0, 0, math.pi / 2), Color3.fromRGB(70, 150, 210), Enum.Material.SmoothPlastic, Enum.PartType.Cylinder) -- Glass renders white from above
	-- Playground: slide and swings
	for _, p in { Vector3.new(-117, 0, 122), Vector3.new(-113, 0, 122), Vector3.new(-117, 0, 126), Vector3.new(-113, 0, 126) } do
		part(park, "SlidePost", Vector3.new(0.4, 5, 0.4), CFrame.new(p + Vector3.new(0, 3, 0)), Color3.fromRGB(240, 200, 60), Enum.Material.Metal)
	end
	part(park, "SlideDeck", Vector3.new(4.4, 0.4, 4.4), CFrame.new(-115, 5.6, 124), Color3.fromRGB(230, 90, 80))
	part(park, "Slide", Vector3.new(3, 0.3, 8), CFrame.new(-115, 3.2, 130.5) * CFrame.Angles(math.rad(-38), 0, 0), Color3.fromRGB(60, 150, 230), Enum.Material.SmoothPlastic)
	for _, x in { -124, -116 } do
		part(park, "SwingPost", Vector3.new(0.4, 7, 0.4), CFrame.new(x, 4, 146), Color3.fromRGB(240, 200, 60), Enum.Material.Metal)
	end
	part(park, "SwingBar", Vector3.new(8.4, 0.4, 0.4), CFrame.new(-120, 7.5, 146), Color3.fromRGB(240, 200, 60), Enum.Material.Metal)
	for _, x in { -122, -118 } do
		part(park, "Chain", Vector3.new(0.1, 4.5, 0.1), CFrame.new(x - 0.6, 5.2, 146), DARK)
		part(park, "Chain", Vector3.new(0.1, 4.5, 0.1), CFrame.new(x + 0.6, 5.2, 146), DARK)
		part(park, "Seat", Vector3.new(1.6, 0.2, 0.8), CFrame.new(x, 3, 146), Color3.fromRGB(230, 90, 80))
	end
	for i, pos in { Vector3.new(-140, 0, 120), Vector3.new(-145, 0, 140), Vector3.new(-120, 0, 165), Vector3.new(-115, 0, 112), Vector3.new(-148, 0, 165) } do
		part(park, `TreeTrunk{i}`, Vector3.new(2, 8, 2), CFrame.new(pos + Vector3.new(0, 4.5, 0)), Color3.fromRGB(140, 100, 65), Enum.Material.Wood)
		part(park, `TreeTop{i}`, Vector3.new(9, 9, 9), CFrame.new(pos + Vector3.new(0, 11.5, 0)), Color3.fromRGB(80, 150, 70), Enum.Material.Grass, Enum.PartType.Ball)
	end
	local benchCF = CFrame.lookAt(Vector3.new(-131, 0.55, 150), Vector3.new(-138, 0.55, 160))
	part(park, "BenchSeat", Vector3.new(6, 0.5, 2), benchCF * CFrame.new(0, 2, 0), Color3.fromRGB(140, 100, 65), Enum.Material.WoodPlanks)
	part(park, "BenchBack", Vector3.new(6, 2, 0.4), benchCF * CFrame.new(0, 3.2, 0.9), Color3.fromRGB(140, 100, 65), Enum.Material.WoodPlanks)
	part(park, "BenchLegs", Vector3.new(5, 1.8, 1.6), benchCF * CFrame.new(0, 0.9, 0), DARK, Enum.Material.Metal)
end

local count = #town:GetDescendants()
return `Town phase 1 built: {#buildings:GetChildren()} buildings, {#lamps:GetChildren()} lamps, {count} instances.`
