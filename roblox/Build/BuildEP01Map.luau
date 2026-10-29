-- BuildEP01Map
-- Builds a blocking-out version of the EP01 town in Edit mode: run it with the Studio MCP
-- execute_luau tool (datamodel Edit) or paste it into the Command Bar.
-- Safe to re-run: it deletes the previous EP01_Map, Markers and cast first.
--
-- Layout (studs), seen from above, +Z toward the viewer:
--   z = -80  Bakery street: Bakery (x=-75), houses with Door_1..Door_4 (x=-45..45), Baker's house (x=75)
--   z = -60  road
--   z =   0  Town square: plaza, fountain at the centre, benches, crowd area
-- The camera markers are invisible parts in workspace.Markers, named to match ep01-shot-list.md,
-- so the shot scripts can say CameraRig.play({ from = { pos = "Markers.Cam_Square_A", ... } }).

local Players = game:GetService("Players")

local PALETTE = {
	plaza = Color3.fromRGB(196, 190, 178),
	road = Color3.fromRGB(70, 72, 80),
	sidewalk = Color3.fromRGB(170, 170, 165),
	grass = Color3.fromRGB(110, 170, 90),
	houses = {
		Color3.fromRGB(214, 120, 100), Color3.fromRGB(120, 160, 205), Color3.fromRGB(235, 205, 120),
		Color3.fromRGB(150, 195, 150), Color3.fromRGB(205, 160, 200),
	},
	bakery = Color3.fromRGB(240, 220, 185),
	roof = Color3.fromRGB(80, 60, 55),
	door = Color3.fromRGB(110, 70, 45),
	windowDark = Color3.fromRGB(35, 45, 60),
	windowLit = Color3.fromRGB(255, 200, 120),
	stone = Color3.fromRGB(150, 150, 155),
	water = Color3.fromRGB(80, 160, 220),
	wood = Color3.fromRGB(140, 100, 65),
}

for _, name in { "EP01_Map", "Markers", "Hero", "Baker", "Influencer" } do
	local old = workspace:FindFirstChild(name)
	if old then
		old:Destroy()
	end
end

local map = Instance.new("Model")
map.Name = "EP01_Map"
map.Parent = workspace

local markers = Instance.new("Folder")
markers.Name = "Markers"
markers.Parent = workspace

local function folder(name: string): Folder
	local f = Instance.new("Folder")
	f.Name = name
	f.Parent = map
	return f
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

-- Invisible marker. `lookAt` aims its front face, so the marker can double as a camera mount.
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

-- Ground
local ground = folder("Ground")
part(ground, "Grass", Vector3.new(400, 1, 300), CFrame.new(0, -0.45, -40), PALETTE.grass, Enum.Material.Grass)
part(ground, "Plaza", Vector3.new(90, 1, 90), CFrame.new(0, 0.05, 0), PALETTE.plaza, Enum.Material.Cobblestone)
part(ground, "Road", Vector3.new(260, 1, 14), CFrame.new(0, 0.05, -57), PALETTE.road, Enum.Material.Asphalt)
part(ground, "Sidewalk", Vector3.new(260, 1.4, 8), CFrame.new(0, 0.2, -66), PALETTE.sidewalk, Enum.Material.Concrete)
part(ground, "PlazaPath", Vector3.new(12, 1, 10), CFrame.new(0, 0.05, -50), PALETTE.plaza, Enum.Material.Cobblestone)

-- Town square
local square = folder("TownSquare")
part(square, "FountainBase", Vector3.new(3, 16, 16), CFrame.new(0, 1.5, 0) * CFrame.Angles(0, 0, math.rad(90)), PALETTE.stone, Enum.Material.Slate, Enum.PartType.Cylinder)
part(square, "FountainWater", Vector3.new(0.4, 14, 14), CFrame.new(0, 2.9, 0) * CFrame.Angles(0, 0, math.rad(90)), PALETTE.water, Enum.Material.Glass, Enum.PartType.Cylinder).Transparency = 0.3
part(square, "FountainPillar", Vector3.new(7, 2.5, 2.5), CFrame.new(0, 6, 0) * CFrame.Angles(0, 0, math.rad(90)), PALETTE.stone, Enum.Material.Slate, Enum.PartType.Cylinder)
part(square, "FountainBowl", Vector3.new(1, 6, 6), CFrame.new(0, 9.5, 0) * CFrame.Angles(0, 0, math.rad(90)), PALETTE.stone, Enum.Material.Slate, Enum.PartType.Cylinder)
for i, x in { -26, 26 } do
	for j, z in { -18, 18 } do
		local bench = Instance.new("Model")
		bench.Name = `Bench_{i}{j}`
		bench.Parent = square
		local facing = CFrame.lookAt(Vector3.new(x, 0, z), Vector3.new(0, 0, 0))
		part(bench, "Seat", Vector3.new(8, 0.6, 2.5), facing * CFrame.new(0, 2, 0), PALETTE.wood, Enum.Material.WoodPlanks)
		part(bench, "Back", Vector3.new(8, 2.5, 0.5), facing * CFrame.new(0, 3.4, 1.1), PALETTE.wood, Enum.Material.WoodPlanks)
		part(bench, "LegL", Vector3.new(0.6, 2, 2), facing * CFrame.new(-3.3, 1, 0), PALETTE.stone)
		part(bench, "LegR", Vector3.new(0.6, 2, 2), facing * CFrame.new(3.3, 1, 0), PALETTE.stone)
	end
end
for i, pos in { Vector3.new(-40, 0, -40), Vector3.new(40, 0, -40), Vector3.new(-40, 0, 40), Vector3.new(40, 0, 40) } do
	part(square, `TreeTrunk_{i}`, Vector3.new(2, 8, 2), CFrame.new(pos + Vector3.new(0, 4, 0)), PALETTE.wood, Enum.Material.Wood)
	part(square, `TreeTop_{i}`, Vector3.new(9, 9, 9), CFrame.new(pos + Vector3.new(0, 11, 0)), Color3.fromRGB(80, 150, 70), Enum.Material.Grass, Enum.PartType.Ball)
end

-- A house facing +Z (toward the road). Returns the doorstep position.
local function house(parent: Instance, name: string, x: number, z: number, color: Color3, w: number?, h: number?): Vector3
	local width, height, depth = w or 22, h or 16, 18
	local model = Instance.new("Model")
	model.Name = name
	model.Parent = parent
	local front = z + depth / 2
	part(model, "Body", Vector3.new(width, height, depth), CFrame.new(x, height / 2, z), color, Enum.Material.Brick)
	part(model, "Roof", Vector3.new(width + 2, 1.5, depth + 2), CFrame.new(x, height + 0.75, z), PALETTE.roof, Enum.Material.Slate)
	part(model, "Door", Vector3.new(4.5, 7.5, 0.4), CFrame.new(x, 3.75, front + 0.2), PALETTE.door, Enum.Material.Wood)
	part(model, "Step", Vector3.new(7, 0.8, 3), CFrame.new(x, 0.4, front + 1.5), PALETTE.stone, Enum.Material.Concrete)
	for i, wx in { x - width / 4 - 1, x + width / 4 + 1 } do
		local win = part(model, `Window_{i}`, Vector3.new(4.5, 4.5, 0.3), CFrame.new(wx, height * 0.62, front + 0.15), PALETTE.windowDark, Enum.Material.Glass)
		win:SetAttribute("StoryKitWindow", true) -- lit/unlit by the shot scripts via Neon + warm colour
	end
	return Vector3.new(x, 0.8, front + 2.5)
end

-- Bakery street
local street = folder("BakeryStreet")
local bakeryStep = house(street, "Bakery", -75, -81,PALETTE.bakery, 26, 18)
do
	local bakery = street:FindFirstChild("Bakery") :: Model
	local sign = part(bakery, "Sign", Vector3.new(14, 3, 0.4), CFrame.new(-75, 15, -71.6), PALETTE.wood, Enum.Material.Wood)
	local gui = Instance.new("SurfaceGui")
	gui.Face = Enum.NormalId.Front
	gui.Parent = sign
	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Text = "BAKERY"
	label.TextScaled = true
	label.FontFace = Font.fromEnum(Enum.Font.GothamBlack)
	label.TextColor3 = Color3.fromRGB(255, 240, 215)
	label.Parent = gui
	-- Warm light inside the front window, on for most shots, off for shot 13.
	local light = Instance.new("PointLight")
	light.Name = "BakeryLight"
	light.Color = PALETTE.windowLit
	light.Range = 18
	light.Brightness = 2
	light.Parent = bakery:FindFirstChild("Window_1")
end
local doorsteps = {}
for i, x in { -45, -15, 15, 45 } do
	doorsteps[i] = house(street, `House_{i}`, x, -81,PALETTE.houses[i])
end
local bakerStep = house(folder("BakerHouse"), "BakerHouse", 75, -81,PALETTE.houses[5], 20, 15)

-- Markers (names match ep01-shot-list.md)
-- The Hero stands off-centre so the fountain pillar never grows out of their head.
local heroPos = Vector3.new(12, 3, 14)
marker("Mark_Fountain", Vector3.new(heroPos.X, 0.5, heroPos.Z))
marker("Mark_Crowd", Vector3.new(0, 0.5, 26))
marker("Mark_Bakery", bakeryStep)
for i, step in doorsteps do
	marker(`Door_{i}`, step)
end
marker("Door_Baker", bakerStep)

local heroHead = heroPos + Vector3.new(0, 2, 0)
marker("Cam_Square_A", Vector3.new(12, 3, 32), heroHead) -- low, in front of the Hero
marker("Cam_Square_B", Vector3.new(40, 12, 34), heroHead) -- high three-quarter view
marker("Cam_Square_Crane", Vector3.new(0, 70, 60), Vector3.new(0, 0, 0)) -- shot 02 crane start
marker("Cam_Street_A", Vector3.new(-55, 5, -66), doorsteps[1]) -- shot 04 tracking pan start
marker("Cam_Street_B", Vector3.new(55, 5, -66), doorsteps[4]) -- pan end
marker("Cam_Street_Top", Vector3.new(0, 55, -72), Vector3.new(0, 0, -76)) -- shots 06 and 13: same framing
marker("Cam_BakerWindow", bakerStep + Vector3.new(-6, 5, 8), bakerStep + Vector3.new(0, 4, -6)) -- shot 14
marker("Cam_Town_Crane", Vector3.new(0, 140, 140), Vector3.new(0, 0, -40)) -- shot 18 end of crane

-- Cast: plain R15 rigs to dress later (body colours give each a readable silhouette).
local function cast(name: string, pos: Vector3, colors: { head: Color3, torso: Color3, legs: Color3 })
	local desc = Instance.new("HumanoidDescription")
	desc.HeadColor = colors.head
	desc.LeftArmColor = colors.head
	desc.RightArmColor = colors.head
	desc.TorsoColor = colors.torso
	desc.LeftLegColor = colors.legs
	desc.RightLegColor = colors.legs
	local ok, rig = pcall(function()
		return Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R15)
	end)
	if not ok or not rig then
		warn(`BuildEP01Map: couldn't create {name} ({rig}). Add it with Avatar > Rig Builder instead.`)
		return
	end
	rig.Name = name
	rig:PivotTo(CFrame.lookAt(pos, pos + Vector3.new(0, 0, 1)))
	rig.Parent = workspace
	local root = rig:FindFirstChild("HumanoidRootPart") :: BasePart?
	if root then
		root.Anchored = true -- stays put until a shot script animates it
	end
end

local skin = Color3.fromRGB(234, 190, 150)
cast("Hero", heroPos, { head = skin, torso = Color3.fromRGB(70, 90, 140), legs = Color3.fromRGB(40, 40, 50) })
cast("Baker", bakeryStep + Vector3.new(4, 2.2, 1), { head = skin, torso = Color3.fromRGB(245, 245, 240), legs = Color3.fromRGB(90, 90, 100) })
cast("Influencer", Vector3.new(-8, 3, 6), { head = skin, torso = Color3.fromRGB(255, 80, 150), legs = Color3.fromRGB(30, 30, 35) })

-- Move the default spawn off the plaza so the player never lands in a shot.
local spawn = workspace:FindFirstChild("SpawnLocation")
if spawn then
	spawn.CFrame = CFrame.new(150, 0.5, 80)
end

return `EP01 map built: {#map:GetDescendants()} parts and models, {#markers:GetChildren()} markers.`
